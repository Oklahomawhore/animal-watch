package main

import (
	"encoding/json"
	"encoding/xml"
	"fmt"
	"math"
	"math/rand"
	"time"
)

// EventSimulator 事件模拟器
type EventSimulator struct {
	CameraID      string
	TenantID      string
	ShedID        string
	BaseTimestamp time.Time
}

// NewEventSimulator 创建模拟器
func NewEventSimulator(cameraID, tenantID, shedID string) *EventSimulator {
	return &EventSimulator{
		CameraID:      cameraID,
		TenantID:      tenantID,
		ShedID:        shedID,
		BaseTimestamp: time.Now().Add(-24 * time.Hour), // 从昨天开始
	}
}

// GenerateISAPIXML 生成ISAPI XML事件
func (s *EventSimulator) GenerateISAPIXML(eventType string, timestamp time.Time, intensity float64) []byte {
	// 根据活动强度生成区域数
	regionCount := int(intensity*4) + 1
	if regionCount > 4 {
		regionCount = 4
	}
	
	// 生成区域坐标
	regions := make([]DetectionRegion, regionCount)
	for i := 0; i < regionCount; i++ {
		coords := []RegionCoordinate{
			{PositionX: rand.Intn(100) + i*50, PositionY: rand.Intn(100) + i*30},
			{PositionX: rand.Intn(100) + i*50 + 20, PositionY: rand.Intn(100) + i*30},
		}
		
		regions[i] = DetectionRegion{
			RegionID:            i + 1,
			Sensitivity:         50 + rand.Intn(50),
			RegionCoordinatesList: RegionCoordinatesList{RegionCoordinates: coords},
		}
	}
	
	event := ISAPIEvent{
		Version:     "2.0",
		IPAddress:   "192.168.1.100",
		PortNo:      80,
		Protocol:    "HTTP",
		MacAddress:  "00:23:45:67:89:AB",
		ChannelID:   1,
		DateTime:    timestamp.Format("2006-01-02T15:04:05-07:00"),
		ActivePostCount: rand.Intn(5) + 1,
		EventType:   eventType,
		EventState:  "active",
		DetectionRegionList: DetectionRegionList{DetectionRegions: regions},
	}
	
	data, _ := xml.MarshalIndent(event, "", "  ")
	return data
}

// ActivityPattern 活动模式类型
type ActivityPattern int

const (
	PatternIdle       ActivityPattern = iota // 静止模式
	PatternLowActivity                       // 低活动模式
	PatternNormal                            // 正常活动模式
	PatternHighActivity                      // 高活动模式
	PatternAbnormalDrop                      // 异常骤降模式
	PatternAbnormalSpike                     // 异常激增模式
)

// GenerateScenario 生成场景化数据
func (s *EventSimulator) GenerateScenario(pattern ActivityPattern, duration time.Duration) [][]byte {
	events := make([][]byte, 0)
	interval := 5 * time.Second // 基础间隔
	
	now := s.BaseTimestamp
	end := now.Add(duration)
	
	for now.Before(end) {
		var intensity float64
		var shouldGenerate bool
		
		switch pattern {
		case PatternIdle:
			// 静止：很少触发，强度低
			shouldGenerate = rand.Float64() < 0.05
			intensity = 0.1
			
		case PatternLowActivity:
			// 低活动：偶尔触发，低强度
			shouldGenerate = rand.Float64() < 0.2
			intensity = 0.3
			
		case PatternNormal:
			// 正常活动：规律触发，中等强度
			shouldGenerate = rand.Float64() < 0.5
			intensity = 0.5 + rand.Float64()*0.3
			
		case PatternHighActivity:
			// 高活动：频繁触发，高强度
			shouldGenerate = rand.Float64() < 0.8
			intensity = 0.7 + rand.Float64()*0.3
			
		case PatternAbnormalDrop:
			// 异常骤降：前高后低
			halfway := now.Add(duration / 2)
			if now.Before(halfway) {
				shouldGenerate = rand.Float64() < 0.7
				intensity = 0.6
			} else {
				shouldGenerate = rand.Float64() < 0.1
				intensity = 0.1
			}
			
		case PatternAbnormalSpike:
			// 异常激增：前低后高
			halfway := now.Add(duration / 2)
			if now.Before(halfway) {
				shouldGenerate = rand.Float64() < 0.2
				intensity = 0.3
			} else {
				shouldGenerate = rand.Float64() < 0.9
				intensity = 0.9
			}
		}
		
		if shouldGenerate {
			xml := s.GenerateISAPIXML("motionDetection", now, intensity)
			events = append(events, xml)
		}
		
		now = now.Add(interval)
	}
	
	return events
}

// GenerateDayData 生成一天的数据（模拟真实林麝活动模式）
func (s *EventSimulator) GenerateDayData() [][]byte {
	events := make([][]byte, 0)
	
	// 林麝活动模式：
	// 06:00-09:00: 清晨活动（进食）- 高活动
	// 09:00-12:00: 上午休息 - 低活动
	// 12:00-14:00: 午间进食 - 中等活动
	// 14:00-17:00: 下午休息 - 低活动
	// 17:00-19:00: 傍晚活动（进食）- 高活动
	// 19:00-06:00: 夜间休息 - 静止
	
	day := s.BaseTimestamp.Truncate(24 * time.Hour)
	
	schedules := []struct {
		start  time.Duration
		end    time.Duration
		pattern ActivityPattern
	}{
		{0 * time.Hour, 6 * time.Hour, PatternIdle},        // 00:00-06:00 夜间休息
		{6 * time.Hour, 9 * time.Hour, PatternHighActivity}, // 06:00-09:00 清晨进食
		{9 * time.Hour, 12 * time.Hour, PatternLowActivity}, // 09:00-12:00 上午休息
		{12 * time.Hour, 14 * time.Hour, PatternNormal},     // 12:00-14:00 午间进食
		{14 * time.Hour, 17 * time.Hour, PatternLowActivity},// 14:00-17:00 下午休息
		{17 * time.Hour, 19 * time.Hour, PatternHighActivity},// 17:00-19:00 傍晚进食
		{19 * time.Hour, 24 * time.Hour, PatternIdle},       // 19:00-24:00 夜间休息
	}
	
	for _, schedule := range schedules {
		start := day.Add(schedule.start)
		duration := schedule.end - schedule.start
		scenarioEvents := s.GenerateScenario(schedule.pattern, duration)
		events = append(events, scenarioEvents...)
	}
	
	return events
}

// GenerateSickAnimalData 生成病畜数据（活动量持续下降）
func (s *EventSimulator) GenerateSickAnimalData(days int) [][]byte {
	events := make([][]byte, 0)
	
	for day := 0; day < days; day++ {
		s.BaseTimestamp = s.BaseTimestamp.Add(24 * time.Hour)
		
		// 随着时间推移，活动量逐渐下降
		declineFactor := float64(day) / float64(days)
		
		dayEvents := s.GenerateDayData()
		
		// 随机删除一些事件来模拟活动量下降
		filteredEvents := make([][]byte, 0)
		for _, event := range dayEvents {
			if rand.Float64() > (declineFactor * 0.5) {
				filteredEvents = append(filteredEvents, event)
			}
		}
		
		events = append(events, filteredEvents...)
	}
	
	return events
}

// EventBatch 事件批次（用于测试）
type EventBatch struct {
	TenantID string          `json:"tenant_id"`
	ShedID   string          `json:"shed_id"`
	CameraID string          `json:"camera_id"`
	Events   []SimulatedEvent `json:"events"`
}

type SimulatedEvent struct {
	Timestamp   int64   `json:"timestamp"`
	EventType   string  `json:"event_type"`
	Intensity   float64 `json:"intensity"`
	XMLData     string  `json:"xml_data"`
}

// ExportToJSON 导出为JSON格式（用于测试）
func (s *EventSimulator) ExportToJSON(events [][]byte) []byte {
	simEvents := make([]SimulatedEvent, len(events))
	
	for i, xmlData := range events {
		// 解析XML获取时间
		var isapi ISAPIEvent
		xml.Unmarshal(xmlData, &isapi)
		
		timestamp, _ := time.Parse("2006-01-02T15:04:05-07:00", isapi.DateTime)
		
		simEvents[i] = SimulatedEvent{
			Timestamp: timestamp.Unix(),
			EventType: isapi.EventType,
			Intensity: float64(len(isapi.DetectionRegionList.DetectionRegions)) / 4.0,
			XMLData:   string(xmlData),
		}
	}
	
	batch := EventBatch{
		TenantID: s.TenantID,
		ShedID:   s.ShedID,
		CameraID: s.CameraID,
		Events:   simEvents,
	}
	
	data, _ := json.MarshalIndent(batch, "", "  ")
	return data
}

// Statistics 统计信息
type Statistics struct {
	TotalEvents     int     `json:"total_events"`
	Duration        int     `json:"duration_hours"`
	EventsPerHour   float64 `json:"events_per_hour"`
	PeakHour        int     `json:"peak_hour"`
	PeakEventCount  int     `json:"peak_event_count"`
}

// CalculateStatistics 计算统计数据
func CalculateStatistics(events [][]byte) Statistics {
	if len(events) == 0 {
		return Statistics{}
	}
	
	// 解析所有事件
	timestamps := make([]time.Time, len(events))
	for i, xmlData := range events {
		var isapi ISAPIEvent
		xml.Unmarshal(xmlData, &isapi)
		timestamps[i], _ = time.Parse("2006-01-02T15:04:05-07:00", isapi.DateTime)
	}
	
	// 计算时间范围
	var minTime, maxTime time.Time
	for i, ts := range timestamps {
		if i == 0 || ts.Before(minTime) {
			minTime = ts
		}
		if i == 0 || ts.After(maxTime) {
			maxTime = ts
		}
	}
	
	duration := maxTime.Sub(minTime).Hours()
	
	// 计算每小时事件数
	hourlyCount := make(map[int]int)
	for _, ts := range timestamps {
		hour := ts.Hour()
		hourlyCount[hour]++
	}
	
	// 找出峰值小时
	peakHour := 0
	peakCount := 0
	for hour, count := range hourlyCount {
		if count > peakCount {
			peakCount = count
			peakHour = hour
		}
	}
	
	return Statistics{
		TotalEvents:    len(events),
		Duration:       int(duration),
		EventsPerHour:  float64(len(events)) / duration,
		PeakHour:       peakHour,
		PeakEventCount: peakCount,
	}
}

// Main function for testing
func main() {
	rand.Seed(time.Now().UnixNano())
	
	fmt.Println("=== 林麝活动量事件模拟器 ===\n")
	
	// 场景1: 正常健康林麝
	fmt.Println("【场景1】正常健康林麝的一天活动模式")
	sim1 := NewEventSimulator("CAM_001", "tenant_farm_001", "shed_A1")
	normalEvents := sim1.GenerateDayData()
	stats1 := CalculateStatistics(normalEvents)
	fmt.Printf("总事件数: %d\n", stats1.TotalEvents)
	fmt.Printf("平均每小时: %.1f 次\n", stats1.EventsPerHour)
	fmt.Printf("活动高峰: %d:00 (%d 次)\n\n", stats1.PeakHour, stats1.PeakEventCount)
	
	// 场景2: 静止模式
	fmt.Println("【场景2】静止模式测试（病畜/夜间）")
	sim2 := NewEventSimulator("CAM_002", "tenant_farm_001", "shed_A2")
	idleEvents := sim2.GenerateScenario(PatternIdle, 2*time.Hour)
	stats2 := CalculateStatistics(idleEvents)
	fmt.Printf("总事件数: %d\n", stats2.TotalEvents)
	fmt.Printf("平均每小时: %.1f 次\n\n", stats2.EventsPerHour)
	
	// 场景3: 异常骤降
	fmt.Println("【场景3】异常活动量骤降（疾病早期）")
	sim3 := NewEventSimulator("CAM_003", "tenant_farm_001", "shed_A3")
	dropEvents := sim3.GenerateScenario(PatternAbnormalDrop, 2*time.Hour)
	stats3 := CalculateStatistics(dropEvents)
	fmt.Printf("总事件数: %d\n", stats3.TotalEvents)
	fmt.Printf("平均每小时: %.1f 次\n\n", stats3.EventsPerHour)
	
	// 场景4: 病畜多天数据
	fmt.Println("【场景4】病畜3天活动量变化")
	sim4 := NewEventSimulator("CAM_004", "tenant_farm_001", "shed_A4")
	sickEvents := sim4.GenerateSickAnimalData(3)
	stats4 := CalculateStatistics(sickEvents)
	fmt.Printf("总事件数: %d\n", stats4.TotalEvents)
	fmt.Printf("平均每天: %.1f 次\n", float64(stats4.TotalEvents)/3)
	fmt.Printf("平均每小时: %.1f 次\n\n", stats4.EventsPerHour)
	
	// 导出示例JSON
	fmt.Println("【导出示例】前3个事件的JSON格式:")
	if len(normalEvents) > 0 {
		sample := EventBatch{
			TenantID: sim1.TenantID,
			ShedID:   sim1.ShedID,
			CameraID: sim1.CameraID,
		}
		for i := 0; i < min(3, len(normalEvents)); i++ {
			var isapi ISAPIEvent
			xml.Unmarshal(normalEvents[i], &isapi)
			ts, _ := time.Parse("2006-01-02T15:04:05-07:00", isapi.DateTime)
			sample.Events = append(sample.Events, SimulatedEvent{
				Timestamp: ts.Unix(),
				EventType: isapi.EventType,
				Intensity: float64(len(isapi.DetectionRegionList.DetectionRegions)) / 4.0,
				XMLData:   string(normalEvents[i]),
			})
		}
		jsonData, _ := json.MarshalIndent(sample, "", "  ")
		fmt.Println(string(jsonData))
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
