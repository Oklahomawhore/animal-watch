package main

import (
	"bytes"
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api/write"
)

// CameraConfig 摄像头配置
type CameraConfig struct {
	ID         string `json:"id"`
	TenantID   string `json:"tenant_id"`
	ShedID     string `json:"shed_id"`
	IP         string `json:"ip"`
	Port       int    `json:"port"`
	Username   string `json:"username"`
	Password   string `json:"password"`
	Protocol   string `json:"protocol"` // http/https
}

// ISAPIClient ISAPI客户端
type ISAPIClient struct {
	config     CameraConfig
	httpClient *http.Client
}

// NewISAPIClient 创建ISAPI客户端
func NewISAPIClient(config CameraConfig) *ISAPIClient {
	return &ISAPIClient{
		config: config,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetEvents 从摄像头获取事件
func (c *ISAPIClient) GetEvents(ctx context.Context, startTime, endTime time.Time) ([]ISAPIEvent, error) {
	// 构建ISAPI请求URL
	url := fmt.Sprintf("%s://%s:%d/ISAPI/Event/notification/alertStream", 
		c.config.Protocol, c.config.IP, c.config.Port)
	
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	
	// 基本认证
	req.SetBasicAuth(c.config.Username, c.config.Password)
	
	// 添加查询参数
	q := req.URL.Query()
	q.Add("startTime", startTime.Format("2006-01-02T15:04:05-07:00"))
	q.Add("endTime", endTime.Format("2006-01-02T15:04:05-07:00"))
	req.URL.RawQuery = q.Encode()
	
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}
	
	// 解析响应（可能是多个XML文档）
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	
	return parseMultipleEvents(body)
}

// GetEventCapabilities 获取摄像头事件能力
func (c *ISAPIClient) GetEventCapabilities(ctx context.Context) (*EventCapabilities, error) {
	url := fmt.Sprintf("%s://%s:%d/ISAPI/Event/capabilities", 
		c.config.Protocol, c.config.IP, c.config.Port)
	
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	
	req.SetBasicAuth(c.config.Username, c.config.Password)
	
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	
	var caps EventCapabilities
	if err := xml.Unmarshal(body, &caps); err != nil {
		return nil, err
	}
	
	return &caps, nil
}

// parseMultipleEvents 解析多个XML事件（海康可能返回多个XML）
func parseMultipleEvents(data []byte) ([]ISAPIEvent, error) {
	events := make([]ISAPIEvent, 0)
	
	// 分割多个XML文档
	docs := bytes.Split(data, []byte("<?xml version="))
	
	for i, doc := range docs {
		if i == 0 && len(doc) == 0 {
			continue // 跳过空内容
		}
		
		// 重新添加XML头
		if i > 0 {
			doc = append([]byte("<?xml version="), doc...)
		}
		
		var event ISAPIEvent
		if err := xml.Unmarshal(doc, &event); err != nil {
			continue // 忽略解析错误，继续处理下一个
		}
		
		// 验证必要字段
		if event.EventType != "" && event.DateTime != "" {
			events = append(events, event)
		}
	}
	
	return events, nil
}

// EventCapabilities 事件能力
type EventCapabilities struct {
	XMLName       xml.Name `xml:"EventCap"`
	SupportEventTypes []string `xml:"isSupportEventType"`
}

// DataCollector 数据收集器
type DataCollector struct {
	cameras     []CameraConfig
	influxClient influxdb2.Client
	writeAPI    api.WriteAPI
	
	// 收集间隔
	collectInterval time.Duration
	
	// 并发控制
	workerPool  int
	sem         chan struct{}
}

// NewDataCollector 创建数据收集器
func NewDataCollector(cameras []CameraConfig, influxURL, influxToken string) *DataCollector {
	client := influxdb2.NewClient(influxURL, influxToken)
	writeAPI := client.WriteAPI("linshe", "raw_events")
	
	return &DataCollector{
		cameras:         cameras,
		influxClient:    client,
		writeAPI:        writeAPI,
		collectInterval: 30 * time.Second, // 每30秒收集一次
		workerPool:      10,
		sem:             make(chan struct{}, 10),
	}
}

// Start 启动数据收集
func (dc *DataCollector) Start(ctx context.Context) {
	ticker := time.NewTicker(dc.collectInterval)
	defer ticker.Stop()
	
	// 立即执行一次
	dc.collectAll(ctx)
	
	for {
		select {
		case <-ticker.C:
			dc.collectAll(ctx)
		case <-ctx.Done():
			return
		}
	}
}

// collectAll 收集所有摄像头数据
func (dc *DataCollector) collectAll(ctx context.Context) {
	var wg sync.WaitGroup
	
	for _, camera := range dc.cameras {
		wg.Add(1)
		
		// 使用信号量控制并发
		dc.sem <- struct{}{}
		
		go func(cam CameraConfig) {
			defer wg.Done()
			defer func() { <-dc.sem }()
			
			if err := dc.collectFromCamera(ctx, cam); err != nil {
				log.Printf("Failed to collect from camera %s: %v", cam.ID, err)
			}
		}(camera)
	}
	
	wg.Wait()
}

// collectFromCamera 从单个摄像头收集数据
func (dc *DataCollector) collectFromCamera(ctx context.Context, camera CameraConfig) error {
	client := NewISAPIClient(camera)
	
	// 获取最近一个收集间隔内的事件
	endTime := time.Now()
	startTime := endTime.Add(-dc.collectInterval * 2) // 稍微重叠避免遗漏
	
	events, err := client.GetEvents(ctx, startTime, endTime)
	if err != nil {
		return err
	}
	
	// 存储原始事件
	for _, event := range events {
		dc.storeRawEvent(camera, event)
	}
	
	log.Printf("Collected %d events from camera %s", len(events), camera.ID)
	return nil
}

// storeRawEvent 存储原始事件到InfluxDB
func (dc *DataCollector) storeRawEvent(camera CameraConfig, event ISAPIEvent) {
	ts, err := time.Parse("2006-01-02T15:04:05-07:00", event.DateTime)
	if err != nil {
		ts = time.Now()
	}
	
	// 区域数
	regionCount := len(event.DetectionRegionList.DetectionRegions)
	
	// 提取灵敏度
	sensitivity := 0
	if regionCount > 0 {
		sensitivity = event.DetectionRegionList.DetectionRegions[0].Sensitivity
	}
	
	point := write.NewPoint(
		"hikvision_events",
		map[string]string{
			"tenant_id": camera.TenantID,
			"shed_id":   camera.ShedID,
			"camera_id": camera.ID,
			"event_type": event.EventType,
		},
		map[string]interface{}{
			"region_count":      regionCount,
			"sensitivity":       sensitivity,
			"active_post_count": event.ActivePostCount,
			"ip_address":        event.IPAddress,
		},
		ts,
	)
	
	dc.writeAPI.WritePoint(point)
}

// Close 关闭收集器
func (dc *DataCollector) Close() {
	dc.writeAPI.Flush()
	dc.influxClient.Close()
}

// MockDataCollector 模拟数据收集器（用于测试）
type MockDataCollector struct {
	cameras     []CameraConfig
	influxClient influxdb2.Client
	writeAPI    api.WriteAPI
	simulators  map[string]*EventSimulator
}

// NewMockDataCollector 创建模拟收集器
func NewMockDataCollector(cameras []CameraConfig, influxURL, influxToken string) *MockDataCollector {
	client := influxdb2.NewClient(influxURL, influxToken)
	writeAPI := client.WriteAPI("linshe", "raw_events")
	
	simulators := make(map[string]*EventSimulator)
	for _, cam := range cameras {
		simulators[cam.ID] = NewEventSimulator(cam.ID, cam.TenantID, cam.ShedID)
	}
	
	return &MockDataCollector{
		cameras:      cameras,
		influxClient: client,
		writeAPI:     writeAPI,
		simulators:   simulators,
	}
}

// Start 启动模拟数据生成
func (mc *MockDataCollector) Start(ctx context.Context) {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			mc.generateMockData()
		case <-ctx.Done():
			return
		}
	}
}

// generateMockData 生成模拟数据
func (mc *MockDataCollector) generateMockData() {
	for _, camera := range mc.cameras {
		sim := mc.simulators[camera.ID]
		
		// 根据时间决定活动模式
		hour := time.Now().Hour()
		var pattern ActivityPattern
		
		switch {
		case hour >= 6 && hour < 9:
			pattern = PatternHighActivity // 清晨进食
		case hour >= 9 && hour < 12:
			pattern = PatternLowActivity  // 上午休息
		case hour >= 12 && hour < 14:
			pattern = PatternNormal       // 午间进食
		case hour >= 14 && hour < 17:
			pattern = PatternLowActivity  // 下午休息
		case hour >= 17 && hour < 19:
			pattern = PatternHighActivity // 傍晚进食
		default:
			pattern = PatternIdle         // 夜间休息
		}
		
		// 生成10秒的数据
		events := sim.GenerateScenario(pattern, 10*time.Second)
		
		// 存储
		for _, xmlData := range events {
			var event ISAPIEvent
			xml.Unmarshal(xmlData, &event)
			mc.storeRawEvent(camera, event)
		}
		
		if len(events) > 0 {
			log.Printf("[Mock] Generated %d events for camera %s (pattern: %v)", 
				len(events), camera.ID, pattern)
		}
	}
}

func (mc *MockDataCollector) storeRawEvent(camera CameraConfig, event ISAPIEvent) {
	ts, _ := time.Parse("2006-01-02T15:04:05-07:00", event.DateTime)
	
	point := write.NewPoint(
		"hikvision_events",
		map[string]string{
			"tenant_id":  camera.TenantID,
			"shed_id":    camera.ShedID,
			"camera_id":  camera.ID,
			"event_type": event.EventType,
		},
		map[string]interface{}{
			"region_count": len(event.DetectionRegionList.DetectionRegions),
		},
		ts,
	)
	
	mc.writeAPI.WritePoint(point)
}

func (mc *MockDataCollector) Close() {
	mc.writeAPI.Flush()
	mc.influxClient.Close()
}

// CameraLoader 摄像头配置加载器
func LoadCameraConfigs(path string) ([]CameraConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	
	var configs []CameraConfig
	if err := json.Unmarshal(data, &configs); err != nil {
		return nil, err
	}
	
	return configs, nil
}

// CreateDefaultCameras 创建默认摄像头配置（用于测试）
func CreateDefaultCameras() []CameraConfig {
	return []CameraConfig{
		{
			ID:       "CAM_001",
			TenantID: "tenant_001",
			ShedID:   "shed_A1",
			IP:       "192.168.1.101",
			Port:     80,
			Username: "admin",
			Password: "admin123",
			Protocol: "http",
		},
		{
			ID:       "CAM_002",
			TenantID: "tenant_001",
			ShedID:   "shed_A1",
			IP:       "192.168.1.102",
			Port:     80,
			Username: "admin",
			Password: "admin123",
			Protocol: "http",
		},
		{
			ID:       "CAM_003",
			TenantID: "tenant_001",
			ShedID:   "shed_A2",
			IP:       "192.168.1.103",
			Port:     80,
			Username: "admin",
			Password: "admin123",
			Protocol: "http",
		},
	}
}

func main() {
	// 加载配置
	var cameras []CameraConfig
	var err error
	
	if len(os.Args) > 1 {
		// 从文件加载
		cameras, err = LoadCameraConfigs(os.Args[1])
		if err != nil {
			log.Printf("Failed to load config, using defaults: %v", err)
			cameras = CreateDefaultCameras()
		}
	} else {
		cameras = CreateDefaultCameras()
	}
	
	log.Printf("Loaded %d camera configs", len(cameras))
	
	// 创建收集器
	influxURL := getEnv("INFLUX_URL", "http://localhost:8086")
	influxToken := getEnv("INFLUX_TOKEN", "")
	
	useMock := getEnv("USE_MOCK", "true") == "true"
	
	var collector interface {
		Start(ctx context.Context)
		Close()
	}
	
	if useMock {
		log.Println("Using MOCK data collector")
		collector = NewMockDataCollector(cameras, influxURL, influxToken)
	} else {
		log.Println("Using REAL camera data collector")
		collector = NewDataCollector(cameras, influxURL, influxToken)
	}
	defer collector.Close()
	
	// 启动收集
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	sigterm := make(chan os.Signal, 1)
	signal.Notify(sigterm, syscall.SIGINT, syscall.SIGTERM)
	
	go func() {
		<-sigterm
		log.Println("Shutting down collector...")
		cancel()
	}()
	
	collector.Start(ctx)
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
