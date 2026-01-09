"""
生成PWA应用图标
将512x512的图标缩放到所需的各种尺寸
"""

from PIL import Image
import os

# 图标尺寸列表
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def generate_icons(source_image_path, output_dir):
    """
    从源图片生成所有尺寸的图标
    
    Args:
        source_image_path: 源图片路径（建议512x512或更大）
        output_dir: 输出目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 打开源图片
    try:
        img = Image.open(source_image_path)
        print(f"✅ 成功打开源图片: {source_image_path}")
        print(f"   原始尺寸: {img.size}")
    except Exception as e:
        print(f"❌ 无法打开图片: {e}")
        return
    
    # 确保图片是RGBA模式
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # 生成各种尺寸的图标
    for size in ICON_SIZES:
        try:
            # 创建圆角图标（可选）
            icon = img.resize((size, size), Image.Resampling.LANCZOS)
            
            # 保存图标
            output_path = os.path.join(output_dir, f'icon-{size}x{size}.png')
            icon.save(output_path, 'PNG', optimize=True)
            print(f"✅ 生成图标: icon-{size}x{size}.png")
        except Exception as e:
            print(f"❌ 生成 {size}x{size} 图标失败: {e}")
    
    print(f"\n🎉 图标生成完成！输出目录: {output_dir}")


def create_placeholder_icon(output_dir):
    """
    创建占位符图标（如果没有源图片）
    """
    from PIL import ImageDraw, ImageFont
    
    os.makedirs(output_dir, exist_ok=True)
    
    for size in ICON_SIZES:
        # 创建渐变背景
        img = Image.new('RGBA', (size, size), (102, 126, 234, 255))
        draw = ImageDraw.Draw(img)
        
        # 绘制圆角矩形边框
        padding = size // 10
        draw.rectangle(
            [padding, padding, size-padding, size-padding],
            outline=(255, 255, 255, 200),
            width=max(2, size // 64)
        )
        
        # 添加文字
        font_size = size // 4
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.load_default()
        
        text = "📦"
        
        # 获取文字边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 居中绘制
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
        # 保存
        output_path = os.path.join(output_dir, f'icon-{size}x{size}.png')
        img.save(output_path, 'PNG', optimize=True)
        print(f"✅ 生成占位图标: icon-{size}x{size}.png")
    
    print(f"\n🎉 占位图标生成完成！")


if __name__ == '__main__':
    import sys
    
    # 输出目录
    output_dir = 'web/static/icons'
    
    # 检查是否提供了源图片路径
    if len(sys.argv) > 1:
        source_image = sys.argv[1]
        if os.path.exists(source_image):
            generate_icons(source_image, output_dir)
        else:
            print(f"❌ 源图片不存在: {source_image}")
            print("正在生成占位图标...")
            create_placeholder_icon(output_dir)
    else:
        print("📦 物流视频管理系统 - 图标生成工具")
        print("\n用法:")
        print("  python generate_icons.py <源图片路径>")
        print("\n示例:")
        print("  python generate_icons.py logo.png")
        print("\n未提供源图片，生成占位图标...")
        create_placeholder_icon(output_dir)
