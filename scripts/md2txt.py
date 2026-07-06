"""将 Markdown 转为纯文本"""
import re

with open(r'D:\人力资源项目\docs\使用手册.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
for line in lines:
    line = line.rstrip()
    # 跳过分隔线和 HTML 注释
    if line.strip() == '---':
        continue
    # 去掉 Markdown 格式
    line = line.replace('**', '')
    line = line.replace('*', '')
    line = line.replace('`', '')
    line = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', line)
    out.append(line)

with open(r'D:\人力资源项目\docs\使用手册.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('Done')
