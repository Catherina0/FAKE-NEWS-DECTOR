#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from main.text_analysis import analyze_source_quality, analyze_language_neutrality
from main.result_formatter import print_formatted_result

# 创建测试数据
result = {
    '总体评分': 0.4,
    '各项评分': {
        'AI内容检测': 0.5, 
        '语言中立性': 0.3, 
        '来源可信度': 0.4, 
        '引用质量': 0.3, 
        '交叉验证': 0.87
    },
    '详细分析': {
        'AI内容检测': ['AI内容检测的详细分析'],
        '语言中立性': ['语言中立性的详细分析'],
        '来源可信度': ['来源可信度的详细分析'],
        '引用质量': ['引用质量的详细分析'],
        '交叉验证': ['交叉验证的详细分析']
    },
    '评分详情': {},
    '问题': [],
    '警告': []
}

# 打印格式化结果
print_formatted_result(result) 