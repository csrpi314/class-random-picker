import csv
import random

# 配置
ROW_COUNT = 200  # 生成学生数量
OUTPUT_NAME = "normal_student_200.csv"
SURNAMES = ["张","李","王","刘","陈","杨","黄","赵","周","吴","徐","孙","马","朱","胡","郭","何","高","林"]
NAMES = ["伟","芳","娜","强","敏","静","磊","洋","宇","欣","浩","彤","鑫","佳","博"]

def random_name():
    s = random.choice(SURNAMES)
    n = random.choice(NAMES) + random.choice(NAMES) if random.random()>0.5 else random.choice(NAMES)
    return s + n

def random_weight():
    # 0 ~ 99.5，步长0.5
    val = round(random.uniform(0,99.5)*2)/2
    return val

def main():
    rows = []
    rows.append(["学号","姓名","性别","权重"])
    for sid in range(1, ROW_COUNT+1):
        name = random_name()
        sex = "男" if random.random()>0.45 else "女"
        w = random_weight()
        rows.append([sid, name, sex, w])
    with open(OUTPUT_NAME, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"生成完成：{OUTPUT_NAME}，共{ROW_COUNT}名学生")

if __name__ == "__main__":
    random.seed(42)
    main()