#!/usr/bin/env python3
"""
修复matplotlib中文字体显示问题
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import sys
import os

def fix_chinese_font():
    """修复中文字体显示"""
    print("🔧 修复matplotlib中文字体显示...")
    
    # 查找系统中可用的中文字体
    available_fonts = []
    
    # macOS常见中文字体
    macos_fonts = [
        'PingFang SC',
        'Hiragino Sans GB',
        'STHeiti',
        'Arial Unicode MS',
        'SimHei',
        'Microsoft YaHei'
    ]
    
    print("📋 检查可用字体:")
    for font_name in macos_fonts:
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            if font_path and os.path.exists(font_path):
                available_fonts.append(font_name)
                print(f"   ✅ {font_name}: {font_path}")
            else:
                print(f"   ❌ {font_name}: 未找到")
        except:
            print(f"   ❌ {font_name}: 检查失败")
    
    if available_fonts:
        # 使用第一个可用字体
        selected_font = available_fonts[0]
        print(f"\n✅ 选择字体: {selected_font}")
        
        # 配置matplotlib
        plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams['font.sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 测试中文显示
        test_chinese_display(selected_font)
        
        return selected_font
    else:
        print("❌ 未找到可用的中文字体")
        return None

def test_chinese_display(font_name):
    """测试中文显示效果"""
    print(f"\n🧪 测试中文显示效果...")
    
    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # 测试各种中文文本
        test_texts = [
            "TradeFan专业回测系统",
            "收益率分析",
            "风险控制指标",
            "投资建议报告"
        ]
        
        for i, text in enumerate(test_texts):
            ax.text(0.1, 0.8 - i*0.15, text, fontsize=14, 
                   transform=ax.transAxes, fontweight='bold')
        
        ax.set_title(f'中文字体测试 - {font_name}', fontsize=16, fontweight='bold')
        ax.text(0.5, 0.3, '如果您能正常看到这些中文，说明字体配置成功！', 
               ha='center', va='center', transform=ax.transAxes, 
               fontsize=12, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # 保存测试图片
        test_path = "results/font_test.png"
        os.makedirs('results', exist_ok=True)
        plt.savefig(test_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ 字体测试图片已保存: {test_path}")
        print("请查看该图片确认中文显示是否正常")
        
    except Exception as e:
        print(f"❌ 字体测试失败: {str(e)}")

if __name__ == "__main__":
    fix_chinese_font()
