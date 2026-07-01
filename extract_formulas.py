import zipfile
import xml.etree.ElementTree as ET

doc_path = r'c:\Users\licl45\Desktop\testTRAE\testword.docx'

# OMML 命名空间
MATH_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def extract_math_text(elem):
    """
    递归提取 OMML 公式元素的文本表示
    """
    results = []
    
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
    
    for child in elem:
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        
        if child_tag == 'r':
            # Math Run: 提取文本
            for t_elem in child.findall(f'{{{MATH_NS}}}t'):
                text = t_elem.text or ''
                results.append(text)
        
        elif child_tag == 'f':
            # Fraction: 分数
            num_text = ''
            den_text = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'num':
                    num_text = extract_math_text(part)
                elif part_tag == 'den':
                    den_text = extract_math_text(part)
            results.append(f'({num_text})/({den_text})')
        
        elif child_tag == 'sSup':
            # Superscript: 上标
            base = ''
            sup = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'e':
                    base = extract_math_text(part)
                elif part_tag == 'sup':
                    sup = extract_math_text(part)
            results.append(f'{base}^{sup}')
        
        elif child_tag == 'sSub':
            # Subscript: 下标
            base = ''
            sub = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'e':
                    base = extract_math_text(part)
                elif part_tag == 'sub':
                    sub = extract_math_text(part)
            results.append(f'{base}_{sub}')
        
        elif child_tag == 'sSubSup':
            # Subscript + Superscript
            base = ''
            sub = ''
            sup = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'e':
                    base = extract_math_text(part)
                elif part_tag == 'sub':
                    sub = extract_math_text(part)
                elif part_tag == 'sup':
                    sup = extract_math_text(part)
            results.append(f'{base}_{sub}^{sup}')
        
        elif child_tag == 'rad':
            # Radical: 根号
            deg_text = ''
            e_text = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'deg':
                    deg_text = extract_math_text(part)
                elif part_tag == 'e':
                    e_text = extract_math_text(part)
            if deg_text:
                results.append(f'({deg_text})√({e_text})')
            else:
                results.append(f'√({e_text})')
        
        elif child_tag == 'nary':
            # N-ary operator: 积分/求和/乘积
            base = ''
            sub = ''
            sup = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'e':
                    base = extract_math_text(part)
                elif part_tag == 'sub':
                    sub = extract_math_text(part)
                elif part_tag == 'sup':
                    sup = extract_math_text(part)
                elif part_tag == 'naryPr':
                    for pr_child in part:
                        pr_tag = pr_child.tag.split('}')[-1] if '}' in pr_child.tag else pr_child.tag
                        if pr_tag == 'chr':
                            chr_val = pr_child.get(f'{{{MATH_NS}}}val', '')
            
            # 尝试从属性中获取操作符
            nary_op = '∫'  # 默认积分
            for pr_child in child.findall(f'{{{MATH_NS}}}naryPr'):
                chr_elem = pr_child.find(f'{{{MATH_NS}}}chr')
                if chr_elem is not None:
                    char_val = chr_elem.get(f'{{{MATH_NS}}}val', '')
                    if char_val == '∫':
                        nary_op = '∫'
                    elif char_val == '∑':
                        nary_op = '∑'
                    elif char_val == '∏':
                        nary_op = '∏'
            
            results.append(f'{nary_op}_{sub}^{sup}({base})')
        
        elif child_tag == 'groupChr':
            # Group character: 括号组
            inner = extract_math_text(child)
            results.append(f'({inner})')
        
        elif child_tag == 'acc':
            # Accent: 重音符号
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'bar':
            # Bar: 上划线
            inner = extract_math_text(child)
            results.append(f'overline({inner})')
        
        elif child_tag == 'd':
            # Delimiter: 分隔符
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'eqArr':
            # Equation Array
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'limLow':
            # Lower limit
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'limUpp':
            # Upper limit
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'func':
            # Function
            fname = ''
            fe = ''
            for part in child:
                part_tag = part.tag.split('}')[-1] if '}' in part.tag else part.tag
                if part_tag == 'fName':
                    fname = extract_math_text(part)
                elif part_tag == 'e':
                    fe = extract_math_text(part)
            if fname and fe:
                results.append(f'{fname}({fe})')
            elif fname:
                results.append(fname)
            elif fe:
                results.append(f'({fe})')
        
        elif child_tag == 'box':
            inner = extract_math_text(child)
            results.append(inner)
        
        elif child_tag == 'borderBox':
            inner = extract_math_text(child)
            results.append(f'box({inner})')
        
        elif child_tag == 'ctrlPr':
            pass  # 忽略控制属性
        
        else:
            inner = extract_math_text(child)
            if inner:
                results.append(inner)
    
    return ''.join(results)


# ============================================================
# 提取并打印所有公式
# ============================================================

print("=" * 70)
print("提取 Word 文档中的 OMML 公式")
print("=" * 70)

with zipfile.ZipFile(doc_path, 'r') as z:
    with z.open('word/document.xml') as f:
        tree = ET.parse(f)

root = tree.getroot()

# 查找所有公式
math_paras = root.findall(f'.//{{{MATH_NS}}}oMathPara')
math_inlines = root.findall(f'.//{{{MATH_NS}}}oMath')

print(f"\n找到 {len(math_paras)} 个公式段落 (oMathPara)")
print(f"找到 {len(math_inlines)} 个公式 (oMath)")
print()

# 全局提取所有 oMath (非嵌套在 oMathPara 中的)
all_math = root.findall(f'.//{{{MATH_NS}}}oMath')

for idx, math_elem in enumerate(all_math, 1):
    formula_text = extract_math_text(math_elem)
    
    # 获取完整 XML 用于调试
    raw_xml = ET.tostring(math_elem, encoding='unicode')
    
    print(f"--- 公式 {idx} ---")
    print(f"  提取文本: {formula_text}")
    print(f"  原始 XML (前 500 字符): {raw_xml[:500]}")
    print()