package main

import (
	"context"
	"encoding/xml"
	"testing"
	"time"

	"github.com/IBM/sarama"
	"github.com/stretchr/testify/assert"
)

// TestParseISAPIEvent 测试ISAPI事件解析
func TestParseISAPIEvent(t *testing.T) {
	xmlData := []byte(`<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0">
	<ipAddress>192.168.1.100</ipAddress>
	<portNo>80</portNo>
	<protocol>HTTP</protocol>
	<macAddress>00:23:45:67:89:AB</macAddress>
	<channelID>1</channelID>
	<dateTime>2025-02-16T10:23:15+08:00</dateTime>
	<activePostCount>3</activePostCount>
	<eventType>motionDetection</eventType>
	<eventState>active</eventState>
	<DetectionRegionList>
		<DetectionRegion>
			<regionID>1</regionID>
			<sensitivity>80</sensitivity>
			<RegionCoordinatesList>
				<RegionCoordinates>
					<positionX>120</positionX>
					<positionY>200</positionY>
				</RegionCoordinates>
			</RegionCoordinatesList>
		</DetectionRegion>
	</DetectionRegionList>
</EventNotificationAlert>`)

	event, err := ParseISAPIEvent(xmlData)
	
	assert.NoError(t, err)
	assert.NotNil(t, event)
	assert.Equal(t, "2.0", event.Version)
	assert.Equal(t, "192.168.1.100", event.IPAddress)
	assert.Equal(t, "00:23:45:67:89:AB", event.MacAddress)
	assert.Equal(t, 1, event.ChannelID)
	assert.Equal(t, "motionDetection", event.EventType)
	assert.Equal(t, "active", event.EventState)
	assert.Equal(t, 3, event.ActivePostCount)
	assert.Len(t, event.DetectionRegionList.DetectionRegions, 1)
	
	region := event.DetectionRegionList.DetectionRegions[0]
	assert.Equal(t, 1, region.RegionID)
	assert.Equal(t, 80, region.Sensitivity)
}

// TestCalculateActivityMetrics 测试活动量计算
func TestCalculateActivityMetrics(t *testing.T) {
	ep := &EventProcessor{
		windowDuration: 5 * time.Minute,
	}
	
	now := time.Now()
	
	tests := []struct {
		name           string
		events         []ProcessedEvent
		expectedScore  float64
		expectedLevel  string
	}{
		{
			name:           "空窗口",
			events:         []ProcessedEvent{},
			expectedScore:  0,
			expectedLevel:  "idle",
		},
		{
			name: "低活动量",
			events: []ProcessedEvent{
				{Timestamp: now, RegionCount: 1, Sensitivity: 50},
			},
			expectedScore:  0, // 单次事件在5分钟窗口内，频率极低
			expectedLevel:  "idle",
		},
		{
			name: "中等活动量",
			events: generateEvents(now, 10, 2, 60), // 10个事件，2个区域
			expectedScore:  30, // 预期约30分
			expectedLevel:  "moderate",
		},
		{
			name: "高活动量",
			events: generateEvents(now, 30, 4, 80), // 30个事件，4个区域
			expectedScore:  75, // 预期约75分
			expectedLevel:  "high",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			window := &ActivityWindow{
				CameraID:   "CAM_001",
				TenantID:   "tenant_001",
				ShedID:     "shed_001",
				Events:     tt.events,
				StartTime:  now.Add(-5 * time.Minute),
				LastUpdate: now,
			}
			
			metrics := ep.calculateActivityMetrics(window, tt.events)
			
			assert.Equal(t, tt.expectedLevel, metrics.ActivityLevel, 
				"Activity level mismatch for %s", tt.name)
			
			// 评分允许±10的误差
			if tt.expectedScore > 0 {
				assert.InDelta(t, tt.expectedScore, metrics.ActivityScore, 10,
					"Activity score mismatch for %s", tt.name)
			}
		})
	}
}

// TestClassifyActivityLevel 测试活动量分级
func TestClassifyActivityLevel(t *testing.T) {
	tests := []struct {
		score    float64
		expected string
	}{
		{0, "idle"},
		{10, "idle"},
		{14, "idle"},
		{15, "low"},
		{25, "low"},
		{34, "low"},
		{35, "moderate"},
		{45, "moderate"},
		{54, "moderate"},
		{55, "high"},
		{70, "high"},
		{79, "high"},
		{80, "very_high"},
		{95, "very_high"},
		{100, "very_high"},
	}
	
	for _, tt := range tests {
		t.Run(tt.expected, func(t *testing.T) {
			level := classifyActivityLevel(tt.score)
			assert.Equal(t, tt.expected, level)
		})
	}
}

// TestActivityWindow 测试滑动窗口
func TestActivityWindow(t *testing.T) {
	ep := &EventProcessor{
		windowCache:    make(map[string]*ActivityWindow),
		windowDuration: 5 * time.Minute,
	}
	
	cameraID := "CAM_TEST_001"
	tenantID := "tenant_test"
	now := time.Now()
	
	// 添加事件到窗口
	events := []ProcessedEvent{
		{CameraID: cameraID, TenantID: tenantID, Timestamp: now.Add(-4 * time.Minute), RegionCount: 1},
		{CameraID: cameraID, TenantID: tenantID, Timestamp: now.Add(-3 * time.Minute), RegionCount: 2},
		{CameraID: cameraID, TenantID: tenantID, Timestamp: now.Add(-2 * time.Minute), RegionCount: 1},
	}
	
	for _, event := range events {
		ep.addToWindow(event)
	}
	
	// 验证窗口存在
	ep.windowMutex.RLock()
	window, exists := ep.windowCache[cameraID]
	ep.windowMutex.RUnlock()
	
	assert.True(t, exists)
	assert.NotNil(t, window)
	assert.Equal(t, 3, len(window.Events))
}

// TestSimulator 测试模拟器
func TestSimulator(t *testing.T) {
	sim := NewEventSimulator("CAM_SIM_001", "tenant_sim", "shed_sim")
	
	// 测试生成XML
	xmlData := sim.GenerateISAPIXML("motionDetection", time.Now(), 0.5)
	assert.NotEmpty(t, xmlData)
	
	// 验证XML格式
	var event ISAPIEvent
	err := xml.Unmarshal(xmlData, &event)
	assert.NoError(t, err)
	assert.Equal(t, "motionDetection", event.EventType)
	
	// 测试生成场景
	scenarioEvents := sim.GenerateScenario(PatternNormal, 30*time.Minute)
	assert.NotEmpty(t, scenarioEvents)
	
	// 验证统计数据
	stats := CalculateStatistics(scenarioEvents)
	assert.Greater(t, stats.TotalEvents, 0)
	assert.Greater(t, stats.EventsPerHour, 0.0)
}

// TestSimulatorPatterns 测试不同活动模式
func TestSimulatorPatterns(t *testing.T) {
	sim := NewEventSimulator("CAM_PATTERN", "tenant", "shed")
	
	patterns := []struct {
		name           ActivityPattern
		expectedMinEvents int
		expectedMaxEvents int
	}{
		{PatternIdle, 0, 20},       // 静止模式，事件很少
		{PatternNormal, 50, 200},   // 正常模式，事件适中
		{PatternHighActivity, 150, 400}, // 高活动模式，事件很多
	}
	
	for _, tt := range patterns {
		t.Run(tt.name.String(), func(t *testing.T) {
			events := sim.GenerateScenario(tt.name, 1*time.Hour)
			stats := CalculateStatistics(events)
			
			assert.GreaterOrEqual(t, stats.TotalEvents, tt.expectedMinEvents,
				"Pattern %s should have at least %d events", tt.name, tt.expectedMinEvents)
			assert.LessOrEqual(t, stats.TotalEvents, tt.expectedMaxEvents,
				"Pattern %s should have at most %d events", tt.name, tt.expectedMaxEvents)
		})
	}
}

// TestStatisticsCalculation 测试统计计算
func TestStatisticsCalculation(t *testing.T) {
	// 创建已知模式的测试数据
	sim := NewEventSimulator("CAM_STAT", "tenant", "shed")
	now := time.Now()
	
	// 生成2小时的数据，集中在第1小时
	events := make([][]byte, 0)
	for i := 0; i < 60; i++ {
		ts := now.Add(time.Duration(i) * time.Minute)
		xml := sim.GenerateISAPIXML("motionDetection", ts, 0.5)
		events = append(events, xml)
	}
	
	stats := CalculateStatistics(events)
	
	assert.Equal(t, 60, stats.TotalEvents)
	assert.InDelta(t, 30.0, stats.EventsPerHour, 5.0) // 每小时约30个事件
}

// BenchmarkProcessEvent 性能基准测试
func BenchmarkProcessEvent(b *testing.B) {
	ep := &EventProcessor{
		windowCache:    make(map[string]*ActivityWindow),
		windowDuration: 5 * time.Minute,
		config: Config{
			InfluxURL:    "http://localhost:8086",
			InfluxToken:  "test-token",
			InfluxOrg:    "test",
			InfluxBucket: "test",
		},
	}
	
	// 创建模拟消息
	sim := NewEventSimulator("CAM_BENCH", "tenant", "shed")
	xmlData := sim.GenerateISAPIXML("motionDetection", time.Now(), 0.5)
	
	msg := &sarama.ConsumerMessage{
		Key:       []byte("test-key"),
		Value:     xmlData,
		Topic:     "test-topic",
		Partition: 0,
		Offset:    0,
		Headers: []sarama.RecordHeader{
			{Key: []byte("tenant_id"), Value: []byte("tenant_bench")},
			{Key: []byte("shed_id"), Value: []byte("shed_bench")},
		},
	}
	
	ctx := context.Background()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		ep.ProcessEvent(ctx, msg)
	}
}

// 辅助函数
func generateEvents(baseTime time.Time, count, regionCount, sensitivity int) []ProcessedEvent {
	events := make([]ProcessedEvent, count)
	for i := 0; i < count; i++ {
		events[i] = ProcessedEvent{
			CameraID:    "CAM_001",
			TenantID:    "tenant_001",
			ShedID:      "shed_001",
			EventType:   "motionDetection",
			Timestamp:   baseTime.Add(-time.Duration(count-i) * 10 * time.Second),
			RegionCount: regionCount,
			Sensitivity: sensitivity,
		}
	}
	return events
}

// ActivityPattern 字符串表示
func (ap ActivityPattern) String() string {
	switch ap {
	case PatternIdle:
		return "Idle"
	case PatternLowActivity:
		return "LowActivity"
	case PatternNormal:
		return "Normal"
	case PatternHighActivity:
		return "HighActivity"
	case PatternAbnormalDrop:
		return "AbnormalDrop"
	case PatternAbnormalSpike:
		return "AbnormalSpike"
	default:
		return "Unknown"
	}
}
