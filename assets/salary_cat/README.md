# 月薪猫素材

五张 GIF 由设备使用者提供，分别对应周一到周五，原文件不修改。
它们不因此自动适用工程的 MIT 代码许可；公开或商业再分发需由素材权利人授权。

固件使用 `main/salary_cat.rle`，由 `tools/convert_salary_cats.py` 转换为
112×112 RGB332 RLE，保留循环总时长并减少刷新次数。显示版本将与边缘相连的白底变为透明，
保留猫咪身体内的白色，并过滤原图独立的浅色水印组件；索引 0 为透明。
设备通过调色板将 RGB332 动画转为灰阶显示，保持原有帧数、透明度和播放缓存大小。
此处理针对这五张参考图，替换新素材时需重新检查边缘和浅色细节。需要 Pillow，仅开发转换时使用。

```powershell
python tools/convert_salary_cats.py assets/salary_cat
```

中文设置使用 `main/font_salary16.c`，是 Noto Sans SC 的页面字形子集，
原字体版权为 © 2014–2021 Adobe，保留字体名 Source；按 [SIL OFL 1.1](OFL.txt) 使用。
它仅作用于月薪猫页面，不改变其他页面字体。再生成时使用 OFL 授权的 Noto Sans SC：

```powershell
python tools/generate_salary_font.py <NotoSansSC-VF.ttf路径>
```
