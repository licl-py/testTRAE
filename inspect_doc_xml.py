from docx import Document
import xml.etree.ElementTree as ET
from lxml import etree
import zipfile
import os

doc_path = r'c:\Users\licl45\Desktop\testTRAE\testword.docx'

# 方法1: 直接解压 docx 查看 XML 结构
print("=" * 70)
print("检查文档内部 XML 结构")
print("=" * 70)

with zipfile.ZipFile(doc_path, 'r') as z:
    # 列出所有文件
    print("文档内部文件列表:")
    for f in z.namelist():
        info = z.getinfo(f)
        if 'math' in f.lower():
            print(f"  [MATH] {f} ({info.file_size} bytes)")
        elif 'formula' in f.lower():
            print(f"  [FORMULA] {f} ({info.file_size} bytes)")
        elif 'embed' in f.lower():
            print(f"  [EMBED] {f} ({info.file_size} bytes)")
        else:
            print(f"  {f} ({info.file_size} bytes)")
    
    # 读取 document.xml 检查是否有 OMML 公式
    print("\n检查 document.xml 中的 OMML 公式:")
    with z.open('word/document.xml') as f:
        content = f.read().decode('utf-8')
    
    # 检查是否包含 m:oMath 标签
    if 'm:oMath' in content:
        print("  ✓ 找到 m:oMath 标签 (OMML 公式)")
        # 数一下有多少个
        import re
        match_count = len(re.findall(r'<m:oMath', content))
        print(f"  公式数量: {match_count}")
    else:
        print("  ✗ 未找到 m:oMath 标签")
    
    if 'm:oMathPara' in content:
        print("  ✓ 找到 m:oMathPara 标签")
    
    if 'w:drawing' in content:
        import re
        drawing_count = len(re.findall(r'<w:drawing', content))
        print(f"  ✓ 找到 {drawing_count} 个 w:drawing 元素")
    
    if 'm:oMath' in content:
        # 提取第一个公式的片段
        start = content.find('<m:oMath')
        if start != -1:
            end = content.find('</m:oMath>', start)
            if end != -1:
                snippet = content[start:end + len('</m:oMath>')]
                print(f"\n第一个公式片段 (前500字符):")
                print(snippet[:500])

print("\n\n")

# 方法2: 使用 python-docx 的 lxml 检查
print("=" * 70)
print("使用 python-docx 检查段落 XML")
print("=" * 70)

doc = Document(doc_path)

# 定义 OMML 命名空间
NSMAP = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}

for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if text:
        print(f"\n--- 段落 {i} [{para.style.name}] ---")
        print(f"  文本: {text[:200]}")
        
        # 获取段落 XML
        xml_str = etree.tostring(para._element, pretty_print=True, encoding='unicode')
        
        # 检查是否有 OMML 公式
        has_math = False
        for ns_prefix, ns_uri in NSMAP.items():
            if ns_uri in xml_str:
                pass  # 命名空间存在
        
        if 'm:oMath' in xml_str or 'oMath' in xml_str:
            has_math = True
            print("  ✓ 包含 OMML 公式")
            # 提取公式文本
            math_elements = para._element.findall('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')
            for j, math_elem in enumerate(math_elements):
                math_xml = etree.tostring(math_elem, encoding='unicode')
                print(f"  公式 {j+1} XML (前300字符):")
                print(f"    {math_xml[:300]}")
        
        if 'w:drawing' in xml_str:
            print("  ✓ 包含绘图元素 (可能是公式图片)")
        
        # 打印 XML 片段
        if not has_math and 'drawing' not in xml_str.lower():
            print(f"  XML 片段 (前300字符): {xml_str[:300]}")
        elif not has_math:
            print(f"  XML 片段 (前500字符): {xml_str[:500]}")