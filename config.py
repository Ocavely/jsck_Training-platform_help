import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANSWER_DIR = os.path.join(BASE_DIR, "answer")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STORAGE_FILE = os.path.join(BASE_DIR, ".login_storage.json")
ACCOUNTS_FILE = os.path.join(BASE_DIR, ".accounts.json")

BASE_URL = "http://10.10.15.23"
COURSE_URL = BASE_URL + "/course/view.php?id=14&section=3"
SECTION3_URL = COURSE_URL
SECTION4_URL = BASE_URL + "/course/view.php?id=14&section=4"

ASSIGNMENTS = [
    (387, "387_实训作业1", "regular"),
    (415, "415_字符串拼接", "code_assign"),
    (416, "416_字符串转换", "code_assign"),
    (417, "417_字符串查找与替换", "code_assign"),
    (418, "418_列表元素的增删改", "code_assign"),
    (419, "419_列表元素的排序", "code_assign"),
    (420, "420_数值列表", "code_assign"),
    (421, "421_列表切片", "code_assign"),
    (422, "422_元组的使用", "code_assign"),
    (423, "423_字典的使用", "code_assign"),
    (424, "424_字典的遍历", "code_assign"),
    (425, "425_嵌套", "code_assign"),
    (426, "426_算术比较赋值运算符", "code_assign"),
    (427, "427_逻辑运算符", "code_assign"),
    (428, "428_位运算符", "code_assign"),
    (429, "429_成员运算符", "code_assign"),
    (430, "430_身份运算符", "code_assign"),
    (431, "431_运算符的优先级", "code_assign"),
    (432, "432_顺序结构", "code_assign"),
    (433, "433_选择结构if_else", "code_assign"),
    (434, "434_While循环与break语句", "code_assign"),
]
