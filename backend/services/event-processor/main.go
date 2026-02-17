package main

import (
	"context"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/IBM/sarama"
	"github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api/write"
)

// Config 配置结构
type Config struct {
	KafkaBrokers      string `env:"KAFKA_BROKERS" default:"localhost:9092"`
	KafkaConsumerGroup string `env:"KAFKA_CONSUMER_GROUP" default:"event-processor-group"`
	InputTopic        string `env:"KAFKA_INPUT_TOPIC" default:"hikvision-events-raw"`
	OutputTopic       string `env:"KAFKA_OUTPUT_TOPIC" default:"activity-metrics"`
	
	InfluxURL    string `env:"INFLUX_URL" default:"http://localhost:8086"`
	InfluxToken  string `env:"INFLUX_TOKEN" default:""`
	InfluxOrg    string `env:"INFLUX_ORG" default:"linshe"`
	InfluxBucket string `env:"INFLUX_BUCKET" default:"activity_metrics"`
	
	WorkerCount int `env:"WORKER_COUNT" default:"10"`
	BatchSize   int `env:"BATCH_SIZE" default:"100"`
	BatchTimeoutMs int `env:"BATCH_TIMEOUT_MS" default:"1000"`
}

// ISAPIEvent 海康ISAPI事件结构
type ISAPIEvent struct {
	XMLName     xml.Name `xml:"EventNotificationAlert"`
	Version     string   `xml:"version,attr"`
	IPAddress   string   `xml:"ipAddress"`
	PortNo      int      `xml:"portNo"`
	Protocol    string   `xml:"protocol"`
	MacAddress  string   `xml:"macAddress"`
	ChannelID   int      `xml:"channelID"`
	DateTime    string   `xml:"dateTime"`
	ActivePostCount int  `xml:"activePostCount"`
	EventType   string   `xml:"eventType"`
	EventState  string   `xml:"eventState"`
	DetectionRegionList DetectionRegionList `xml:"DetectionRegionList"`
}

type DetectionRegionList struct {
	DetectionRegions []DetectionRegion `xml:"DetectionRegion"`
}

type DetectionRegion struct {
	RegionID            int                     `xml:"regionID"`
	Sensitivity         int                     `xml:"sensitivity"`
	RegionCoordinatesList RegionCoordinatesList `xml:"RegionCoordinatesList"`
}

type RegionCoordinatesList struct {
	RegionCoordinates []RegionCoordinate `xml:"RegionCoordinates"`
}

type RegionCoordinate struct {
	PositionX int `xml:"positionX"`
	PositionY int `xml:"positionY"`
}

// ProcessedEvent 处理后的事件
type ProcessedEvent struct {
	TenantID        string    `json:"tenant_id"`
	DeviceID        string    `json:"device_id"`
	CameraID        string    `json:"camera_id"`
	ShedID          string    `json:"shed_id"`
	EventType       string    `json:"event_type"`
	Timestamp       time.Time `json:"timestamp"`
	RegionCount     int       `json:"region_count"`
	Sensitivity     int       `json:"sensitivity"`
	ActivePostCount int       `json:"active_post_count"`
	RawData         string    `json:"raw_data"`
}

// ActivityMetrics 活动量指标
type ActivityMetrics struct {
	TenantID       string    `json:"tenant_id"`
	CameraID       string    `json:"camera_id"`
	ShedID         string    `json:"shed_id"`
	Timestamp      time.Time `json:"timestamp"`
	WindowStart    time.Time `json:"window_start"`
	WindowEnd      time.Time `json:"window_end"`
	
	// 活动量指标
	ActivityScore  float64 `json:"activity_score"`   // 0-100 活动量评分
	ActivityLevel  string  `json:"activity_level"`   // idle/low/moderate/high/very_high
	EventCount     int     `json:"event_count"`      // 事件数量
	EventFrequency float64 `json:"event_frequency"`  // 事件频率(次/分钟)
	RegionCoverage int     `json:"region_coverage"`  // 覆盖区域数
	AvgSensitivity float64 `json:"avg_sensitivity"`  // 平均灵敏度
	
	// 原始统计
	RawEventIDs    []string `json:"raw_event_ids"`   // 关联的原始事件ID
}

// EventProcessor 事件处理器
type EventProcessor struct {
	config         Config
	kafkaConsumer  sarama.ConsumerGroup
	kafkaProducer  sarama.SyncProducer
	influxClient   influxdb2.Client
	writeAPI       api.WriteAPI
	
	// 滑动窗口缓存 (按cameraID分窗口)
	windowCache    map[string]*ActivityWindow
	windowMutex    sync.RWMutex
	windowDuration time.Duration
}

// ActivityWindow 活动量计算窗口
type ActivityWindow struct {
	CameraID      string
	TenantID      string
	ShedID        string
	Events        []ProcessedEvent
	StartTime     time.Time
	LastUpdate    time.Time
	mutex         sync.Mutex
}

// NewEventProcessor 创建处理器
func NewEventProcessor(config Config) (*EventProcessor, error) {
	// 创建Kafka消费者
	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Group.Rebalance.Strategy = sarama.BalanceStrategyRoundRobin
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetOldest
	consumerConfig.Consumer.Return.Errors = true
	
	consumer, err := sarama.NewConsumerGroup(
		strings.Split(config.KafkaBrokers, ","),
		config.KafkaConsumerGroup,
		consumerConfig,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create consumer: %w", err)
	}
	
	// 创建Kafka生产者
	producerConfig := sarama.NewConfig()
	producerConfig.Producer.RequiredAcks = sarama.WaitForLocal
	producerConfig.Producer.Retry.Max = 3
	producerConfig.Producer.Return.Successes = true
	
	producer, err := sarama.NewSyncProducer(
		strings.Split(config.KafkaBrokers, ","),
		producerConfig,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create producer: %w", err)
	}
	
	// 创建InfluxDB客户端
	influxClient := influxdb2.NewClient(config.InfluxURL, config.InfluxToken)
	writeAPI := influxClient.WriteAPI(config.InfluxOrg, config.InfluxBucket)
	
	return &EventProcessor{
		config:         config,
		kafkaConsumer:  consumer,
		kafkaProducer:  producer,
		influxClient:   influxClient,
		writeAPI:       writeAPI,
		windowCache:    make(map[string]*ActivityWindow),
		windowDuration: 5 * time.Minute, // 5分钟滑动窗口
	}, nil
}

// ParseISAPIEvent 解析ISAPI XML事件
func ParseISAPIEvent(xmlData []byte) (*ISAPIEvent, error) {
	var event ISAPIEvent
	if err := xml.Unmarshal(xmlData, &event); err != nil {
		return nil, fmt.Errorf("failed to parse XML: %w", err)
	}
	return &event, nil
}

// ProcessEvent 处理单个事件
func (ep *EventProcessor) ProcessEvent(ctx context.Context, rawEvent *sarama.ConsumerMessage) error {
	// 从Kafka消息头获取租户信息
	tenantID := extractTenantID(rawEvent)
	shedID := extractShedID(rawEvent)
	
	// 解析XML
	isapiEvent, err := ParseISAPIEvent(rawEvent.Value)
	if err != nil {
		log.Printf("Failed to parse event: %v", err)
		return err
	}
	
	// 解析时间
	timestamp, err := time.Parse("2006-01-02T15:04:05-07:00", isapiEvent.DateTime)
	if err != nil {
		timestamp = time.Now()
	}
	
	// 创建处理后的事件
	event := ProcessedEvent{
		TenantID:        tenantID,
		DeviceID:        isapiEvent.MacAddress,
		CameraID:        fmt.Sprintf("%s_ch%d", isapiEvent.MacAddress, isapiEvent.ChannelID),
		ShedID:          shedID,
		EventType:       isapiEvent.EventType,
		Timestamp:       timestamp,
		RegionCount:     len(isapiEvent.DetectionRegionList.DetectionRegions),
		ActivePostCount: isapiEvent.ActivePostCount,
		RawData:         string(rawEvent.Value),
	}
	
	// 提取灵敏度（取第一个区域的灵敏度）
	if event.RegionCount > 0 {
		event.Sensitivity = isapiEvent.DetectionRegionList.DetectionRegions[0].Sensitivity
	}
	
	// 添加到滑动窗口
	ep.addToWindow(event)
	
	return nil
}

// addToWindow 添加事件到滑动窗口
func (ep *EventProcessor) addToWindow(event ProcessedEvent) {
	ep.windowMutex.Lock()
	defer ep.windowMutex.Unlock()
	
	window, exists := ep.windowCache[event.CameraID]
	if !exists {
		window = &ActivityWindow{
			CameraID:   event.CameraID,
			TenantID:   event.TenantID,
			ShedID:     event.ShedID,
			Events:     make([]ProcessedEvent, 0),
			StartTime:  event.Timestamp,
			LastUpdate: event.Timestamp,
		}
		ep.windowCache[event.CameraID] = window
	}
	
	window.mutex.Lock()
	window.Events = append(window.Events, event)
	window.LastUpdate = event.Timestamp
	window.mutex.Unlock()
	
	// 检查是否需要触发窗口计算
	if time.Since(window.StartTime) >= ep.windowDuration {
		go ep.calculateAndFlushWindow(event.CameraID)
	}
}

// calculateAndFlushWindow 计算窗口活动量并刷新
func (ep *EventProcessor) calculateAndFlushWindow(cameraID string) {
	ep.windowMutex.Lock()
	window, exists := ep.windowCache[cameraID]
	if !exists {
		ep.windowMutex.Unlock()
		return
	}
	
	// 从缓存中移除（将创建新窗口）
	delete(ep.windowCache, cameraID)
	ep.windowMutex.Unlock()
	
	window.mutex.Lock()
	events := make([]ProcessedEvent, len(window.Events))
	copy(events, window.Events)
	window.mutex.Unlock()
	
	if len(events) == 0 {
		return
	}
	
	// 计算活动量
	metrics := ep.calculateActivityMetrics(window, events)
	
	// 保存到InfluxDB
	ep.saveToInfluxDB(metrics)
	
	// 发送到Kafka下游
	ep.publishMetrics(metrics)
	
	// 检查异常
	ep.detectAnomalies(metrics)
	
	log.Printf("Processed window for camera %s: score=%.2f, level=%s, events=%d",
		cameraID, metrics.ActivityScore, metrics.ActivityLevel, metrics.EventCount)
}

// calculateActivityMetrics 计算活动量指标
func (ep *EventProcessor) calculateActivityMetrics(window *ActivityWindow, events []ProcessedEvent) ActivityMetrics {
	eventCount := len(events)
	if eventCount == 0 {
		return ActivityMetrics{
			TenantID:    window.TenantID,
			CameraID:    window.CameraID,
			ShedID:      window.ShedID,
			Timestamp:   time.Now(),
			WindowStart: window.StartTime,
			WindowEnd:   window.LastUpdate,
			ActivityScore: 0,
			ActivityLevel: "idle",
		}
	}
	
	// 1. 计算时间跨度（秒）
	timeSpan := window.LastUpdate.Sub(window.StartTime).Seconds()
	if timeSpan < 1 {
		timeSpan = 60 // 最小1分钟
	}
	
	// 2. 事件频率 (次/分钟)
	frequency := float64(eventCount) / (timeSpan / 60.0)
	
	// 3. 区域覆盖度（去重后的区域数）
	uniqueRegions := make(map[int]bool)
	totalSensitivity := 0
	for _, event := range events {
		uniqueRegions[event.RegionCount] = true
		totalSensitivity += event.Sensitivity
	}
	regionCoverage := len(uniqueRegions)
	avgSensitivity := float64(totalSensitivity) / float64(eventCount)
	
	// 4. 计算活动量评分 (0-100)
	// 算法：频率权重40% + 事件数量权重30% + 区域覆盖权重20% + 灵敏度权重10%
	frequencyScore := min(frequency*2, 40)           // 频率贡献，上限40分
	countScore := min(float64(eventCount)*0.6, 30)   // 数量贡献，上限30分
	coverageScore := float64(regionCoverage) * 5      // 每个区域5分，上限20分
	sensitivityScore := (avgSensitivity / 100.0) * 10 // 灵敏度贡献，上限10分
	
	activityScore := frequencyScore + countScore + coverageScore + sensitivityScore
	activityScore = min(activityScore, 100) // 封顶100
	
	// 5. 活动等级
	activityLevel := classifyActivityLevel(activityScore)
	
	// 收集事件ID
	rawEventIDs := make([]string, len(events))
	for i, event := range events {
		rawEventIDs[i] = fmt.Sprintf("%s_%d", event.CameraID, event.Timestamp.Unix())
	}
	
	return ActivityMetrics{
		TenantID:       window.TenantID,
		CameraID:       window.CameraID,
		ShedID:         window.ShedID,
		Timestamp:      time.Now(),
		WindowStart:    window.StartTime,
		WindowEnd:      window.LastUpdate,
		ActivityScore:  activityScore,
		ActivityLevel:  activityLevel,
		EventCount:     eventCount,
		EventFrequency: frequency,
		RegionCoverage: regionCoverage,
		AvgSensitivity: avgSensitivity,
		RawEventIDs:    rawEventIDs,
	}
}

// classifyActivityLevel 活动量分级
func classifyActivityLevel(score float64) string {
	switch {
	case score < 15:
		return "idle"       // 静止
	case score < 35:
		return "low"        // 低活动
	case score < 55:
		return "moderate"   // 中等活动
	case score < 80:
		return "high"       // 高活动
	default:
		return "very_high"  // 极高活动
	}
}

// saveToInfluxDB 保存到InfluxDB
func (ep *EventProcessor) saveToInfluxDB(metrics ActivityMetrics) {
	// 创建数据点
	point := write.NewPoint(
		"activity_metrics", // measurement
		map[string]string{  // tags
			"tenant_id": metrics.TenantID,
			"camera_id": metrics.CameraID,
			"shed_id":   metrics.ShedID,
		},
		map[string]interface{}{ // fields
			"activity_score":   metrics.ActivityScore,
			"activity_level":   metrics.ActivityLevel,
			"event_count":      metrics.EventCount,
			"event_frequency":  metrics.EventFrequency,
			"region_coverage":  metrics.RegionCoverage,
			"avg_sensitivity":  metrics.AvgSensitivity,
		},
		metrics.Timestamp,
	)
	
	ep.writeAPI.WritePoint(point)
}

// publishMetrics 发布指标到Kafka
func (ep *EventProcessor) publishMetrics(metrics ActivityMetrics) error {
	data, err := json.Marshal(metrics)
	if err != nil {
		return err
	}
	
	msg := &sarama.ProducerMessage{
		Topic: ep.config.OutputTopic,
		Key:   sarama.StringEncoder(metrics.CameraID),
		Value: sarama.ByteEncoder(data),
		Headers: []sarama.RecordHeader{
			{Key: []byte("tenant_id"), Value: []byte(metrics.TenantID)},
		},
	}
	
	_, _, err = ep.kafkaProducer.SendMessage(msg)
	return err
}

// detectAnomalies 异常检测
func (ep *EventProcessor) detectAnomalies(metrics ActivityMetrics) {
	// TODO: 实现基于历史基线的异常检测
	// 1. 查询该摄像头同时间段的历史平均活动量
	// 2. 比较当前值与基线
	// 3. 触发告警（如果偏差超过阈值）
}

// extractTenantID 从Kafka消息头提取租户ID
func extractTenantID(msg *sarama.ConsumerMessage) string {
	for _, header := range msg.Headers {
		if string(header.Key) == "tenant_id" || string(header.Key) == "X-Tenant-ID" {
			return string(header.Value)
		}
	}
	return "default"
}

// extractShedID 从Kafka消息头提取圈舍ID
func extractShedID(msg *sarama.ConsumerMessage) string {
	for _, header := range msg.Headers {
		if string(header.Key) == "shed_id" {
			return string(header.Value)
		}
	}
	return "unknown"
}

// ConsumerGroupHandler Kafka消费者组处理器
type ConsumerGroupHandler struct {
	processor *EventProcessor
}

func (h *ConsumerGroupHandler) Setup(sarama.ConsumerGroupSession) error   { return nil }
func (h *ConsumerGroupHandler) Cleanup(sarama.ConsumerGroupSession) error { return nil }

func (h *ConsumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		ctx := context.Background()
		if err := h.processor.ProcessEvent(ctx, msg); err != nil {
			log.Printf("Error processing event: %v", err)
		}
		session.MarkMessage(msg, "")
	}
	return nil
}

// Start 启动处理器
func (ep *EventProcessor) Start(ctx context.Context) error {
	handler := &ConsumerGroupHandler{processor: ep}
	
	// 启动窗口刷新定时器
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	go func() {
		for {
			select {
			case <-ticker.C:
				ep.flushAllWindows()
			case <-ctx.Done():
				return
			}
		}
	}()
	
	// 启动Kafka消费
	for {
		err := ep.kafkaConsumer.Consume(ctx, []string{ep.config.InputTopic}, handler)
		if err != nil {
			log.Printf("Error from consumer: %v", err)
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
	}
}

// flushAllWindows 刷新所有窗口
func (ep *EventProcessor) flushAllWindows() {
	ep.windowMutex.RLock()
	cameraIDs := make([]string, 0, len(ep.windowCache))
	for id := range ep.windowCache {
		cameraIDs = append(cameraIDs, id)
	}
	ep.windowMutex.RUnlock()
	
	for _, id := range cameraIDs {
		ep.calculateAndFlushWindow(id)
	}
}

// Close 关闭处理器
func (ep *EventProcessor) Close() error {
	// 刷新所有剩余窗口
	ep.flushAllWindows()
	
	// 关闭资源
	ep.writeAPI.Flush()
	ep.influxClient.Close()
	
	if err := ep.kafkaConsumer.Close(); err != nil {
		return err
	}
	
	return ep.kafkaProducer.Close()
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func main() {
	// 加载配置
	config := Config{
		KafkaBrokers:       getEnv("KAFKA_BROKERS", "localhost:9092"),
		KafkaConsumerGroup: getEnv("KAFKA_CONSUMER_GROUP", "event-processor-group"),
		InputTopic:         getEnv("KAFKA_INPUT_TOPIC", "hikvision-events-raw"),
		OutputTopic:        getEnv("KAFKA_OUTPUT_TOPIC", "activity-metrics"),
		InfluxURL:          getEnv("INFLUX_URL", "http://localhost:8086"),
		InfluxToken:        getEnv("INFLUX_TOKEN", ""),
		InfluxOrg:          getEnv("INFLUX_ORG", "linshe"),
		InfluxBucket:       getEnv("INFLUX_BUCKET", "activity_metrics"),
		WorkerCount:        10,
		BatchSize:          100,
		BatchTimeoutMs:     1000,
	}
	
	// 创建处理器
	processor, err := NewEventProcessor(config)
	if err != nil {
		log.Fatalf("Failed to create processor: %v", err)
	}
	defer processor.Close()
	
	log.Println("Event Processor started")
	
	// 优雅关闭
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	sigterm := make(chan os.Signal, 1)
	signal.Notify(sigterm, syscall.SIGINT, syscall.SIGTERM)
	
	go func() {
		<-sigterm
		log.Println("Shutting down...")
		cancel()
	}()
	
	// 启动处理
	if err := processor.Start(ctx); err != nil {
		log.Fatalf("Processor error: %v", err)
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
