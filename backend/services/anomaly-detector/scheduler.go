package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// Scheduler 调度器
type Scheduler struct {
	collector  *MockDataCollector  // 使用模拟收集器
	detector   *AnomalyDetector
	cameras    []CameraConfig
	
	// 调度间隔
	collectInterval time.Duration
	detectInterval  time.Duration
	baselineInterval time.Duration
}

// NewScheduler 创建调度器
func NewScheduler(cameras []CameraConfig, influxURL, influxToken string) *Scheduler {
	return &Scheduler{
		collector:        NewMockDataCollector(cameras, influxURL, influxToken),
		detector:         NewAnomalyDetector(influxURL, influxToken),
		cameras:          cameras,
		collectInterval:  30 * time.Second,  // 每30秒收集数据
		detectInterval:   5 * time.Minute,   // 每5分钟检测异常
		baselineInterval: 1 * time.Hour,     // 每小时更新基线
	}
}

// Start 启动调度
func (s *Scheduler) Start(ctx context.Context) {
	log.Println("=== 林麝健康监测调度器启动 ===")
	
	// 1. 启动数据收集
	go s.collector.Start(ctx)
	
	// 2. 初始化基线（延迟30秒，等待有数据）
	time.Sleep(30 * time.Second)
	s.initializeBaselines(ctx)
	
	// 3. 启动异常检测定时器
	detectTicker := time.NewTicker(s.detectInterval)
	defer detectTicker.Stop()
	
	// 4. 启动基线更新定时器
	baselineTicker := time.NewTicker(s.baselineInterval)
	defer baselineTicker.Stop()
	
	// 5. 启动报表生成定时器（每天）
	reportTicker := time.NewTicker(24 * time.Hour)
	defer reportTicker.Stop()
	
	for {
		select {
		case <-detectTicker.C:
			s.runAnomalyDetection(ctx)
			
		case <-baselineTicker.C:
			s.updateBaselines(ctx)
			
		case <-reportTicker.C:
			s.generateDailyReport(ctx)
			
		case <-ctx.Done():
			log.Println("Shutting down scheduler...")
			s.collector.Close()
			s.detector.Close()
			return
		}
	}
}

// initializeBaselines 初始化所有摄像头的基线
func (s *Scheduler) initializeBaselines(ctx context.Context) {
	log.Println("Initializing baselines for all cameras...")
	
	for _, cam := range s.cameras {
		_, err := s.detector.CalculateBaseline(ctx, cam.ID, cam.TenantID)
		if err != nil {
			log.Printf("Failed to initialize baseline for %s: %v", cam.ID, err)
		} else {
			log.Printf("Baseline initialized for %s", cam.ID)
		}
	}
}

// runAnomalyDetection 运行异常检测
func (s *Scheduler) runAnomalyDetection(ctx context.Context) {
	log.Println("Running anomaly detection...")
	
	for _, cam := range s.cameras {
		// 获取最新活动量
		// 这里简化处理，实际应从InfluxDB查询
		currentActivity := s.getCurrentActivity(cam.ID, cam.TenantID)
		
		if currentActivity < 0 {
			continue // 没有数据
		}
		
		result, err := s.detector.DetectAnomaly(cam.ID, cam.TenantID, cam.ShedID, currentActivity)
		if err != nil {
			log.Printf("Anomaly detection failed for %s: %v", cam.ID, err)
			continue
		}
		
		// 只输出异常结果
		if result.AnomalyLevel != "normal" {
			log.Printf("🚨 ANOMALY: %s | Level: %s | Score: %.1f | %s",
				result.CameraID,
				result.AnomalyLevel,
				result.AnomalyScore,
				result.Description)
		}
	}
}

// getCurrentActivity 获取当前活动量（简化版）
func (s *Scheduler) getCurrentActivity(cameraID, tenantID string) float64 {
	// 这里应该查询InfluxDB获取最新活动量
	// 简化：返回一个模拟值
	return -1 // 表示未实现
}

// updateBaselines 更新基线
func (s *Scheduler) updateBaselines(ctx context.Context) {
	log.Println("Updating baselines...")
	
	for _, cam := range s.cameras {
		err := s.detector.UpdateBaseline(ctx, cam.ID, cam.TenantID)
		if err != nil {
			log.Printf("Failed to update baseline for %s: %v", cam.ID, err)
		}
	}
}

// generateDailyReport 生成日报
func (s *Scheduler) generateDailyReport(ctx context.Context) {
	log.Println("Generating daily report...")
	
	// 统计各租户的数据
	reports := make(map[string]*TenantDailyReport)
	
	for _, cam := range s.cameras {
		if _, exists := reports[cam.TenantID]; !exists {
			reports[cam.TenantID] = &TenantDailyReport{
				TenantID: cam.TenantID,
				Date:     time.Now().Add(-24 * time.Hour),
			}
		}
		
		// 查询该摄像头的统计数据
		stats, exists := s.detector.GetBaselineStats(cam.ID, cam.TenantID)
		if exists {
			reports[cam.TenantID].CameraStats = append(
				reports[cam.TenantID].CameraStats,
				CameraDailyStat{
					CameraID:     cam.ID,
					MeanActivity: stats.Mean,
					AnomalyCount: 0, // 需要从数据库查询
				})
		}
	}
	
	// 输出报表摘要
	for tenantID, report := range reports {
		log.Printf("Daily Report for %s: %d cameras monitored",
			tenantID, len(report.CameraStats))
	}
}

// TenantDailyReport 租户日报
type TenantDailyReport struct {
	TenantID    string
	Date        time.Time
	CameraStats []CameraDailyStat
}

// CameraDailyStat 摄像头日统计
type CameraDailyStat struct {
	CameraID     string
	MeanActivity float64
	AnomalyCount int
}

// TestRunner 测试运行器
func TestRunner() {
	fmt.Println("=== 无监督异常检测算法测试 ===\n")
	
	// 生成测试数据
	data := generateTestData()
	
	// 计算基线统计
	stats := computeTestStats("CAM_TEST", "tenant_test", data)
	
	// 打印统计结果
	fmt.Println("【基线统计结果】")
	fmt.Printf("样本数: %d\n", stats.Count)
	fmt.Printf("平均值: %.2f\n", stats.Mean)
	fmt.Printf("中位数: %.2f\n", stats.Median)
	fmt.Printf("标准差: %.2f\n", stats.StdDev)
	fmt.Printf("最小值: %.2f\n", stats.Min)
	fmt.Printf("最大值: %.2f\n", stats.Max)
	fmt.Printf("P25: %.2f, P75: %.2f, IQR: %.2f\n", stats.P25, stats.P75, stats.IQR)
	fmt.Printf("变异系数: %.2f\n", stats.CV)
	fmt.Printf("偏度: %.2f, 峰度: %.2f\n\n", stats.Skewness, stats.Kurtosis)
	
	// 测试异常检测
	testValues := []float64{
		stats.Mean,                              // 正常值
		stats.Mean + stats.StdDev,               // 略高
		stats.Mean - stats.StdDev,               // 略低
		stats.Mean + 3*stats.StdDev,             // 异常高
		stats.Mean - 3*stats.StdDev,             // 异常低
		stats.Min - 5,                           // 极端低
		stats.Max + 5,                           // 极端高
	}
	
	fmt.Println("【异常检测测试】")
	for _, val := range testValues {
		zScore := (val - stats.Mean) / stats.StdDev
		level, score, method, desc := classifyTestAnomaly(zScore, stats, val)
		
		emoji := "✅"
		if level != "normal" {
			emoji = "🚨"
		}
		
		fmt.Printf("%s Value: %.2f | Z: %.2f | Level: %s | Score: %.1f | Method: %s\n",
			emoji, val, zScore, level, score, method)
		fmt.Printf("   %s\n\n", desc)
	}
}

func generateTestData() []float64 {
	// 生成模拟的7天活动量数据（每小时一个点）
	data := make([]float64, 0, 168)
	
	for day := 0; day < 7; day++ {
		for hour := 0; hour < 24; hour++ {
			var base float64
			
			// 模拟昼夜节律
			switch {
			case hour >= 6 && hour < 9:
				base = 60 + randFloat() * 20   // 清晨进食
			case hour >= 9 && hour < 12:
				base = 20 + randFloat() * 10   // 上午休息
			case hour >= 12 && hour < 14:
				base = 50 + randFloat() * 15   // 午间进食
			case hour >= 14 && hour < 17:
				base = 25 + randFloat() * 10   // 下午休息
			case hour >= 17 && hour < 19:
				base = 55 + randFloat() * 20   // 傍晚进食
			default:
				base = 10 + randFloat() * 5    // 夜间休息
			}
			
			data = append(data, base)
		}
	}
	
	return data
}

func computeTestStats(cameraID, tenantID string, data []float64) *BaselineStats {
	n := len(data)
	sorted := make([]float64, n)
	copy(sorted, data)
	sortFloat64s(sorted)
	
	mean := calculateMean(data)
	variance := calculateVariance(data, mean)
	stdDev := math.Sqrt(variance)
	
	return &BaselineStats{
		CameraID:   cameraID,
		TenantID:   tenantID,
		Count:      n,
		Mean:       mean,
		Median:     calculatePercentile(sorted, 50),
		StdDev:     stdDev,
		Variance:   variance,
		Min:        sorted[0],
		Max:        sorted[n-1],
		Range:      sorted[n-1] - sorted[0],
		P25:        calculatePercentile(sorted, 25),
		P50:        calculatePercentile(sorted, 50),
		P75:        calculatePercentile(sorted, 75),
		P90:        calculatePercentile(sorted, 90),
		P95:        calculatePercentile(sorted, 95),
		P99:        calculatePercentile(sorted, 99),
		CV:         stdDev / mean,
		Skewness:   calculateSkewness(data, mean, stdDev),
		Kurtosis:   calculateKurtosis(data, mean, stdDev),
		IQR:        calculatePercentile(sorted, 75) - calculatePercentile(sorted, 25),
	}
}

func classifyTestAnomaly(zScore float64, baseline *BaselineStats, current float64) (string, float64, string, string) {
	absZScore := math.Abs(zScore)
	
	if absZScore > 2.5 {
		score := min(absZScore/2.5*50, 100)
		level := "warning"
		if absZScore > 3.5 {
			level = "critical"
		}
		
		method := "z_score"
		if zScore > 0 {
			return level, score, method, fmt.Sprintf("活动量异常偏高: %.1f vs 基线%.1f", current, baseline.Mean)
		}
		return level, score, method, fmt.Sprintf("活动量异常偏低: %.1f vs 基线%.1f", current, baseline.Mean)
	}
	
	return "normal", 0, "none", "活动量正常"
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func randFloat() float64 {
	return float64(time.Now().UnixNano()%100) / 100.0
}

func sortFloat64s(data []float64) {
	// 简单冒泡排序（测试用）
	n := len(data)
	for i := 0; i < n; i++ {
		for j := 0; j < n-i-1; j++ {
			if data[j] > data[j+1] {
				data[j], data[j+1] = data[j+1], data[j]
			}
		}
	}
}

func main() {
	// 首先运行测试
	TestRunner()
	
	fmt.Println("\n=== 启动实时调度器 ===\n")
	
	// 创建摄像头配置
	cameras := []CameraConfig{
		{ID: "CAM_001", TenantID: "tenant_demo", ShedID: "shed_A1"},
		{ID: "CAM_002", TenantID: "tenant_demo", ShedID: "shed_A1"},
		{ID: "CAM_003", TenantID: "tenant_demo", ShedID: "shed_A2"},
	}
	
	// 创建调度器
	influxURL := getEnv("INFLUX_URL", "http://localhost:8086")
	influxToken := getEnv("INFLUX_TOKEN", "")
	
	scheduler := NewScheduler(cameras, influxURL, influxToken)
	
	// 启动
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	sigterm := make(chan os.Signal, 1)
	signal.Notify(sigterm, syscall.SIGINT, syscall.SIGTERM)
	
	go func() {
		<-sigterm
		log.Println("收到停止信号...")
		cancel()
	}()
	
	scheduler.Start(ctx)
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
