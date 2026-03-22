# 林麝检测算法 - 测试图片汇总

**生成时间**: 2026-03-12 14:41  
**设备数量**: 5个  
**图片总数**: 5张

---

## 设备列表

| 序号 | 设备序列号 | 名称 | 型号 | 通道数 | 状态 |
|------|-----------|------|------|--------|------|
| 1 | GF6830765 | 2区母麝圈 | DS-8864N-R8(C) | 64 | 在线 |
| 2 | GG3425740 | 2区公麝圈 | DS-8864N-R8(C) | 64 | 在线 |
| 3 | FU7533003 | 1区A1侧✕共同区域 | DS-8864N-R8(D) | 64 | 在线 |
| 4 | FT3193224 | 1区A1侧 | DS-8864N-R8(D) | 64 | 在线 |
| 5 | FT4704701 | 1区A2侧 | DS-8864N-R8(D) | 64 | 在线 |

---

## 抓拍图片

### 1. 2区母麝圈 (GF6830765)
- **文件**: `GF6830765_ch1_20260312_144138.jpg`
- **大小**: 632KB
- **通道**: 1
- **图片URL**: https://opencapture.ys7.com/opst/1/open_capture/3/003vFF8GqYnHQYplIWFGEXQpFWZV4uq.jpg

![2区母麝圈](algorithm/data/images/GF6830765_ch1_20260312_144138.jpg)

---

### 2. 2区公麝圈 (GG3425740)
- **文件**: `GG3425740_ch1_20260312_144140.jpg`
- **大小**: 553KB
- **通道**: 1
- **图片URL**: https://opencapture.ys7.com/opst/1/open_capture/3/003vFF8KMoG9QKiSoLXfNwjSnQhu4LK.jpg

![2区公麝圈](algorithm/data/images/GG3425740_ch1_20260312_144140.jpg)

---

### 3. 1区A1侧✕共同区域 (FU7533003)
- **文件**: `FU7533003_ch1_20260312_144142.jpg`
- **大小**: 557KB
- **通道**: 1
- **图片URL**: https://opencapture.ys7.com/opst/1/open_capture/3/003vFF8N1Kgfn4tGSXyaiLZ1xbWHfqQ.jpg

![1区A1侧✕共同区域](algorithm/data/images/FU7533003_ch1_20260312_144142.jpg)

---

### 4. 1区A1侧 (FT3193224)
- **文件**: `FT3193224_ch1_20260312_144143.jpg`
- **大小**: 440KB
- **通道**: 1
- **图片URL**: https://opencapture.ys7.com/opst/1/open_capture/3/003vFF8QguJh4cydaI1Pmmyxdafh2AH.jpg

![1区A1侧](algorithm/data/images/FT3193224_ch1_20260312_144143.jpg)

---

### 5. 1区A2侧 (FT4704701)
- **文件**: `FT4704701_ch1_20260312_144144.jpg`
- **大小**: 543KB
- **通道**: 1
- **图片URL**: https://opencapture.ys7.com/opst/1/open_capture/3/003vFF8TW1IUDjZ3uLWYYWs8Cn8lqS5.jpg

![1区A2侧](algorithm/data/images/FT4704701_ch1_20260312_144144.jpg)

---

## 下一步

1. **数据标注**: 使用 LabelImg 标注图片中的林麝位置
2. **模型训练**: 基于 YOLOv8 训练检测模型
3. **算法测试**: 验证检测效果

## 文件位置

```
lin-she-health-monitor/
└── algorithm/
    └── data/
        └── images/
            ├── GF6830765_ch1_20260312_144138.jpg
            ├── GG3425740_ch1_20260312_144140.jpg
            ├── FU7533003_ch1_20260312_144142.jpg
            ├── FT3193224_ch1_20260312_144143.jpg
            └── FT4704701_ch1_20260312_144144.jpg
```
