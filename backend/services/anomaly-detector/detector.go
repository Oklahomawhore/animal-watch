package main

import (
	"context"
	"fmt"
	"log"
	"math"
	"sort"
	"sync"
	"time"

	"github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"
)

// BaselineStats 基线统计指标
type BaselineStats struct {
	CameraID      string    `json:"camera_id"`
	TenantID      string    `json:"tenant_id"`
	ShedID        string    `json:"shed_id"`
	WindowStart   time.Time `json:"window_start"`
	WindowEnd     time.Time `json:"window_end"`
	
	// 基本统计量
	Count     int     `json:"count"`      // 样本数
	Mean      float64 `json:"mean"`       // 平均值
	Median    float64 `json:"median"`     // 中位数
	StdDev    float64 `json:"std_dev"`    // 标准差
	Variance  float64 `json:"variance"`   // 方差
	Min       float64 `json:"min"`        // 最小值
	Max       float64 `json:"max"`        // 最大值
	Range     float64 `json:"range"`      // 极差
	
	// 百分位数
	P25       float64 `json:"p25"`        // 25%分位数
	P50       float64 `json:"p50"`        // 50%分位数（同Median）
	P75       float64 `json:"p75"`        // 75%分位数
	P90       float64 `json:"p90"`        // 90%分位数
	P95       float64 `json:"p95"`        // 95%分位数
	P99       float64 `json:"p99"`        // 99%分位数
	
	// 变异系数
	CV        float64 `json:"cv"`         // 变异系数（标准差/均值）
	
	// 偏度和峰度
	Skewness  float64 `json:"skewness"`   // 偏度
	Kurtosis  float64 `json:"kurtosis"`   // 峰度
	
	// IQR
	IQR       float64 `json:"iqr"`        // 四分位距 (P75 - P25)
	LowerBound float64 `json:"lower_bound"` // IQR下界 (P25 - 1.5*IQR)
	UpperBound float64 `json:"upper_bound"` // IQR上界 (P75 + 1.5*IQR)
}

// AnomalyResult 异常检测结果
type AnomalyResult struct {
	CameraID      string    `json:"camera_id"`
	TenantID      string    `json:"tenant_id"`
	ShedID        string    `json:"shed_id"`
	Timestamp     time.Time `json:"timestamp"`
	
	// 当前值
	CurrentValue  float64 `json:"current_value"`
	
	// 基线对比
	BaselineMean  float64 `json:"baseline_mean"`
	BaselineStd   float64 `json:"baseline_std"`
	
	// 异常指标
	ZScore        float64 `json:"z_score"`        // Z分数
	Percentile    float64 `json:"percentile"`     // 百分位排名
	
	// 检测方法
	DetectionMethod string `json:"detection_method"`
	
	// 异常等级
	AnomalyLevel  string  `json:"anomaly_level"`  // normal/warning/critical
	AnomalyScore  float64 `json:"anomaly_score"`  // 0-100异常评分
	
	// 说明
	Description   string  `json:"description"`
}

// AnomalyDetector 异常检测器
type AnomalyDetector struct {
	influxClient   influxdb2.Client
	queryAPI       api.QueryAPI
	writeAPI       api.WriteAPI
	
	// 基线缓存
	baselineCache  map[string]*BaselineStats
	baselineMutex  sync.RWMutex
	
	// 配置
	baselineWindow time.Duration  // 基线学习窗口（默认7天）
	minSamples     int            // 最小样本数（默认100）
	zScoreThreshold float64       // Z分数阈值（默认2.5）
}

// NewAnomalyDetector 创建异常检测器
func NewAnomalyDetector(influxURL, influxToken string) *AnomalyDetector {
	client := influxdb2.NewClient(influxURL, influxToken)
	
	return &AnomalyDetector{
		influxClient:    client,
		queryAPI:        client.QueryAPI("linshe"),
		writeAPI:        client.WriteAPI("linshe", "anomalies"),
		baselineCache:   make(map[string]*BaselineStats),
		baselineWindow:  7 * 24 * time.Hour, // 7天历史数据
		minSamples:      100,
		zScoreThreshold: 2.5,
	}
}

// CalculateBaseline 计算基线统计量
func (ad *AnomalyDetector) CalculateBaseline(ctx context.Context, cameraID, tenantID string) (*BaselineStats, error) {
	// 查询历史数据
	query := fmt.Sprintf(`
		from(bucket: "raw_events")
		|> range(start: -%dh)
		|> filter(fn: (r) => r._measurement == "hikvision_events")
		|> filter(fn: (r) => r.camera_id == "%s")
		|> filter(fn: (r) => r.tenant_id == "%s")
		|> filter(fn: (r) => r._field == "region_count")
	`, int(ad.baselineWindow.Hours()), cameraID, tenantID)
	
	result, err := ad.queryAPI.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer result.Close()
	
	// 收集数据
	values := make([]float64, 0)
	for result.Next() {
		if v, ok := result.Record().Value().(float64); ok {
			values = append(values, v)
		}
	}
	
	if len(values) < ad.minSamples {
		return nil, fmt.Errorf("insufficient data: %d samples (min %d required)", 
			len(values), ad.minSamples)
	}
	
	// 计算统计量
	stats := ad.computeStats(cameraID, tenantID, values)
	
	// 缓存结果
	cacheKey := fmt.Sprintf("%s:%s", tenantID, cameraID)
	ad.baselineMutex.Lock()
	ad.baselineCache[cacheKey] = stats
	ad.baselineMutex.Unlock()
	
	return stats, nil
}

// computeStats 计算统计指标
func (ad *AnomalyDetector) computeStats(cameraID, tenantID string, data []float64) *BaselineStats {
	n := len(data)
	
	// 排序用于计算中位数和百分位数
	sorted := make([]float64, n)
	copy(sorted, data)
	sort.Float64s(sorted)
	
	// 基本统计量
	mean := calculateMean(data)
	min := sorted[0]
	max := sorted[n-1]
	
	// 中位数
	median := calculatePercentile(sorted, 50)
	
	// 方差和标准差
	variance := calculateVariance(data, mean)
	stdDev := math.Sqrt(variance)
	
	// 百分位数
	p25 := calculatePercentile(sorted, 25)
	p50 := median
	p75 := calculatePercentile(sorted, 75)
	p90 := calculatePercentile(sorted, 90)
	p95 := calculatePercentile(sorted, 95)
	p99 := calculatePercentile(sorted, 99)
	
	// IQR
	iqr := p75 - p25
	
	// 变异系数
	cv := 0.0
	if mean != 0 {
		cv = stdDev / mean
	}
	
	// 偏度和峰度
	skewness := calculateSkewness(data, mean, stdDev)
	kurtosis := calculateKurtosis(data, mean, stdDev)
	
	return &BaselineStats{
		CameraID:    cameraID,
		TenantID:    tenantID,
		WindowStart: time.Now().Add(-ad.baselineWindow),
		WindowEnd:   time.Now(),
		Count:       n,
		Mean:        mean,
		Median:      median,
		StdDev:      stdDev,
		Variance:    variance,
		Min:         min,
		Max:         max,
		Range:       max - min,
		P25:         p25,
		P50:         p50,
		P75:         p75,
		P90:         p90,
		P95:         p95,
		P99:         p99,
		CV:          cv,
		Skewness:    skewness,
		Kurtosis:    kurtosis,
		IQR:         iqr,
		LowerBound:  p25 - 1.5*iqr,
		UpperBound:  p75 + 1.5*iqr,
	}
}

// DetectAnomaly 检测异常
func (ad *AnomalyDetector) DetectAnomaly(cameraID, tenantID, shedID string, currentValue float64) (*AnomalyResult, error) {
	// 获取基线（优先从缓存）
	cacheKey := fmt.Sprintf("%s:%s", tenantID, cameraID)
	
	ad.baselineMutex.RLock()
	baseline, exists := ad.baselineCache[cacheKey]
	ad.baselineMutex.RUnlock()
	
	if !exists {
		// 重新计算基线
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		
		var err error
		baseline, err = ad.CalculateBaseline(ctx, cameraID, tenantID)
		if err != nil {
			return nil, fmt.Errorf("failed to get baseline: %w", err)
		}
	}
	
	// 计算Z分数
	zScore := 0.0
	if baseline.StdDev > 0 {
		zScore = (currentValue - baseline.Mean) / baseline.StdDev
	}
	
	// 计算百分位排名
	percentile := ad.estimatePercentile(baseline, currentValue)
	
	// 确定异常等级
	level, score, method, description := ad.classifyAnomaly(zScore, baseline, currentValue)
	
	result := &AnomalyResult{
		CameraID:        cameraID,
		TenantID:        tenantID,
		ShedID:          shedID,
		Timestamp:       time.Now(),
		CurrentValue:    currentValue,
		BaselineMean:    baseline.Mean,
		BaselineStd:     baseline.StdDev,
		ZScore:          zScore,
		Percentile:      percentile,
		DetectionMethod: method,
		AnomalyLevel:    level,
		AnomalyScore:    score,
		Description:     description,
	}
	
	// 存储异常结果
	if level != "normal" {
		ad.storeAnomaly(result)
	}
	
	return result, nil
}

// classifyAnomaly 分类异常等级
func (ad *AnomalyDetector) classifyAnomaly(zScore float64, baseline *BaselineStats, current float64) (level string, score float64, method string, desc string) {
	absZScore := math.Abs(zScore)
	
	// 方法1: Z-Score
	if absZScore > ad.zScoreThreshold {
		score = min(absZScore/ad.zScoreThreshold*50, 100)
		
		if absZScore > 3.5 {
			level = "critical"
		} else if absZScore > 2.5 {
			level = "warning"
		}
		
		if zScore > 0 {
			method = "z_score_high"
			desc = fmt.Sprintf("活动量异常偏高: 当前%.1f, 基线%.1f (Z=%.2f)", 
				current, baseline.Mean, zScore)
		} else {
			method = "z_score_low"
			desc = fmt.Sprintf("活动量异常偏低: 当前%.1f, 基线%.1f (Z=%.2f)", 
				current, baseline.Mean, zScore)
		}
		return
	}
	
	// 方法2: IQR
	if current < baseline.LowerBound || current > baseline.UpperBound {
		score = 60.0
		level = "warning"
		method = "iqr_outlier"
		
		if current < baseline.LowerBound {
			desc = fmt.Sprintf("活动量低于IQR下界: 当前%.1f < %.1f", 
				current, baseline.LowerBound)
		} else {
			desc = fmt.Sprintf("活动量高于IQR上界: 当前%.1f > %.1f", 
				current, baseline.UpperBound)
		}
		return
	}
	
	// 方法3: 极端值检测（P99/P1）
	if current > baseline.P99 || current < baseline.P25-(baseline.P75-baseline.P25) {
		score = 50.0
		level = "warning"
		method = "extreme_percentile"
		desc = fmt.Sprintf("活动量处于极端百分位")
		return
	}
	
	// 正常
	level = "normal"
	score = 0.0
	method = "none"
	desc = "活动量正常"
	return
}

// estimatePercentile 估算百分位排名
func (ad *AnomalyDetector) estimatePercentile(baseline *BaselineStats, value float64) float64 {
	if value <= baseline.Min {
		return 0.0
	}
	if value >= baseline.Max {
		return 100.0
	}
	
	// 使用Z分数估算百分位（正态分布假设）
	if baseline.StdDev > 0 {
		zScore := (value - baseline.Mean) / baseline.StdDev
		// 标准正态分布CDF近似
		percentile := 50.0 + 50.0*erf(zScore/math.Sqrt(2))
		return max(0, min(100, percentile))
	}
	
	return 50.0
}

// storeAnomaly 存储异常结果
func (ad *AnomalyDetector) storeAnomaly(result *AnomalyResult) {
	// 这里可以实现存储到InfluxDB或发送告警
	log.Printf("[ANOMALY] %s - %s (Score: %.1f): %s", 
		result.CameraID, result.AnomalyLevel, result.AnomalyScore, result.Description)
}

// BatchDetect 批量检测
func (ad *AnomalyDetector) BatchDetect(ctx context.Context, tenantID string, window time.Duration) ([]*AnomalyResult, error) {
	// 查询所有摄像头的最新活动量
	query := fmt.Sprintf(`
		from(bucket: "activity_metrics")
		|> range(start: -%dm)
		|> filter(fn: (r) => r._measurement == "activity_metrics")
		|> filter(fn: (r) => r.tenant_id == "%s")
		|> filter(fn: (r) => r._field == "activity_score")
		|> last()
	`, int(window.Minutes()), tenantID)
	
	result, err := ad.queryAPI.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer result.Close()
	
	anomalies := make([]*AnomalyResult, 0)
	
	for result.Next() {
		record := result.Record()
		cameraID, _ := record.ValueByKey("camera_id").(string)
		shedID, _ := record.ValueByKey("shed_id").(string)
		
		if value, ok := record.Value().(float64); ok {
			anomaly, err := ad.DetectAnomaly(cameraID, tenantID, shedID, value)
			if err != nil {
				log.Printf("Failed to detect anomaly for %s: %v", cameraID, err)
				continue
			}
			anomalies = append(anomalies, anomaly)
		}
	}
	
	return anomalies, nil
}

// UpdateBaseline 更新基线
func (ad *AnomalyDetector) UpdateBaseline(ctx context.Context, cameraID, tenantID string) error {
	_, err := ad.CalculateBaseline(ctx, cameraID, tenantID)
	return err
}

// GetBaselineStats 获取基线统计
func (ad *AnomalyDetector) GetBaselineStats(cameraID, tenantID string) (*BaselineStats, bool) {
	cacheKey := fmt.Sprintf("%s:%s", tenantID, cameraID)
	
	ad.baselineMutex.RLock()
	defer ad.baselineMutex.RUnlock()
	
	stats, exists := ad.baselineCache[cacheKey]
	return stats, exists
}

// Close 关闭检测器
func (ad *AnomalyDetector) Close() {
	ad.writeAPI.Flush()
	ad.influxClient.Close()
}

// 统计计算辅助函数

func calculateMean(data []float64) float64 {
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func calculateVariance(data []float64, mean float64) float64 {
	sum := 0.0
	for _, v := range data {
		diff := v - mean
		sum += diff * diff
	}
	return sum / float64(len(data))
}

func calculatePercentile(sorted []float64, p float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	
	// 线性插值法
	index := (p / 100.0) * float64(n-1)
	lower := int(math.Floor(index))
	upper := int(math.Ceil(index))
	
	if lower == upper {
		return sorted[lower]
	}
	
	weight := index - float64(lower)
	return sorted[lower]*(1-weight) + sorted[upper]*weight
}

func calculateSkewness(data []float64, mean, stdDev float64) float64 {
	if stdDev == 0 {
		return 0
	}
	
	n := float64(len(data))
	sum := 0.0
	for _, v := range data {
		sum += math.Pow((v-mean)/stdDev, 3)
	}
	
	return sum / n
}

func calculateKurtosis(data []float64, mean, stdDev float64) float64 {
	if stdDev == 0 {
		return 0
	}
	
	n := float64(len(data))
	sum := 0.0
	for _, v := range data {
		sum += math.Pow((v-mean)/stdDev, 4)
	}
	
	return sum/n - 3 //  excess kurtosis
}

// 误差函数（标准正态分布CDF）
func erf(x float64) float64 {
	// Abramowitz and Stegun近似
	a1 := 0.254829592
	a2 := -0.284496736
	a3 := 1.421413741
	a4 := -1.453152027
	a5 := 1.061405429
	p := 0.3275911
	
	sign := 1.0
	if x < 0 {
		sign = -1.0
	}
	x = math.Abs(x)
	
	t := 1.0 / (1.0 + p*x)
	y := 1.0 - (((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*math.Exp(-x*x)
	
	return sign * y
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
