import os, json

from config import ANSWER_DIR

ANSWERS = {
    415: '# coding=utf-8\n# \u83b7\u53d6\u8f93\u5165\u7684\u6e90\u5b57\u7b26\u4e32\nimport sys\nsource_string = []\nfor line in sys.stdin:\n    source_string.append(line)\nsource_string = source_string[0]\nstep1_result = source_string.strip()\nstep2_result = step1_result.title()\nprint(step2_result)\nprint(len(step2_result))',
    416: 'source_string = input()\nsource_string = source_string.strip()\nstep2_result = source_string.title()\nprint(step2_result)\nprint(len(step2_result))',
    417: 'source_string = input()\n# step1\nprint(source_string.find("day"))\n# step2\ns_new = source_string.replace("day", "time")\nprint(s_new)\n# step3 \u6309\u5355\u4e2a\u7a7a\u683c\u5206\u5272\nres = s_new.split(" ")\nprint(res)',
    418: 'guests = []\nwhile True:\n    try:\n        guests.append(input().strip())\n    except:\n        break\ndeleted_guest = guests.pop()\nguests.insert(2, deleted_guest)\ndel guests[1]\nprint(deleted_guest)\nprint(guests)',
    419: 'source_list = []\nwhile True:\n    try:\n        source_list.append(input().strip())\n    except:\n        break\nsource_list.sort()\nprint(source_list)',
    420: 'lower = int(input())\nupper = int(input())\nstep = int(input())\nmy_list = list(range(lower, upper, step))\nprint(len(my_list))\nprint(max(my_list) - min(my_list))',
    421: 'my_menu = []\nwhile True:\n    try:\n        my_menu.append(input())\n    except:\n        break\nprint(my_menu[::3])\nprint(my_menu[-3:])',
    422: 'menu_list = []\nwhile True:\n    try:\n        menu_list.append(input())\n    except:\n        break\nmenu_tuple = tuple(menu_list)\nprint(menu_tuple)\nprint(max(menu_tuple))',
    423: 'menu_dict = {}\nwhile True:\n    try:\n        food = input()\n        price = int(input())\n        menu_dict[food] = price\n    except:\n        break\nmenu_dict["lamb"] = 50\nprint(menu_dict["fish"])\nmenu_dict["fish"] = 100\ndel menu_dict["noodles"]\nprint(menu_dict)',
    424: 'menu_dict = {}\nwhile True:\n    try:\n        food = input()\n        price = int(input())\n        menu_dict[food] = price\n    except:\n        break\nfor key in menu_dict.keys():\n    print(key)\nfor value in menu_dict.values():\n    print(value)',
    425: 'menu1 = {}\nmenu1["fish"] = int(input())\nmenu1["pork"] = int(input())\nmenu_total = [menu1]\nmenu2 = {}\nmenu2["fish"] = menu1["fish"] * 2\nmenu2["pork"] = menu1["pork"] * 2\nmenu_total.append(menu2)\nprint(menu_total)',
    426: 'apple = int(input())\npear = int(input())\nsum_result = apple + pear\nprint(sum_result)\ndiv_result = apple / pear\nprint(div_result)\nexp_result = apple ** 2\nprint(exp_result)\nisequal = (apple == pear)\nprint(isequal)\nismax = (apple >= pear)\nprint(ismax)\nmulti_result = pear * 2\nprint(multi_result)',
    427: 'tom = input()\njerry = input()\nnot_result = not jerry\nprint(not_result)\nand_result = tom and jerry\nprint(and_result)',
    428: 'bitone = int(input())\nbittwo = int(input())\n# \u8ba1\u7b97bitone,bittwo\u6309\u4f4d\u4e0e\uff0c\u5c06\u8fd0\u7b97\u7ed3\u679c\u5b58\u5165result\u53d8\u91cf\nresult = bitone & bittwo\nprint(result)\n\n# \u8ba1\u7b97bitone,bittwo\u6309\u4f4d\u6216\u7684\u4ee3\u7801\uff0c\u5c06\u8fd0\u7b97\u7ed3\u679c\u5b58\u5165result\u53d8\u91cf\nresult = bitone | bittwo\nprint(result)\n\n# \u8ba1\u7b97bitone,bittwo\u6309\u4f4d\u5f02\u6216\u7684\u4ee3\u7801\uff0c\u5c06\u8fd0\u7b97\u7ed3\u679c\u5b58\u5165result\u53d8\u91cf\nresult = bitone ^ bittwo\nprint(result)\n\n# \u8ba1\u7b97bitone\u6309\u4f4d\u53d6\u53cd\u7684\u4ee3\u7801\uff0c\u5e76\u5c06\u8fd0\u7b97\u7ed3\u679c\u5b58\u5165result\u53d8\u91cf\nresult = ~bitone\nprint(result)',
    429: ('me = input()\n'
          'member_list = list(map(str, input().split(\',\')))\n'
          'if (me in member_list):\n'
          '    print("我是篮球社成员")\n'
          'else:\n'
          '    print("我不是篮球社成员")\n'
          'if (me not in member_list):\n'
          '    print("我不是篮球社成员")\n'
          'else:\n'
          '    print("我是篮球社成员")'),
    430: ('addressone = int(input())\n'
          'addresstwo = int(input())\n'
          'addressthree = int(input())\n'
          'if(addressone is addresstwo):\n'
          '    print("变量addressone与变量addresstwo有相同的存储单元")\n'
          'else:\n'
          '    print("变量addressone与变量addresstwo的存储单元不同")\n'
          'if(addresstwo is not addressthree):\n'
          '    print("变量addresstwo与变量addressthree的存储单元不同")\n'
          'else:\n'
          '    print("变量addresstwo与变量addressthree有相同的存储单元")'),
    431: 'var1 = int(input())\nvar2 = int(input())\nvar3 = int(input())\nvar4 = int(input())\nresult = (var1 * 4 + var2) * var3\nprint(result)\nresult = ((var1 & var2) + var3) * var4\nprint(result)',
    432: 'a = int(input())\nb = int(input())\nc = int(input())\na, b = b, a\nprint(a + c)',
    433: ('workYear = int(input())\n'
          'if workYear < 5:\n'
          '    print("工资涨幅为0")\n'
          'elif workYear >= 5 and workYear < 10:\n'
          '    print("工资涨幅为5%")\n'
          'elif workYear >= 10 and workYear < 15:\n'
          '    print("工资涨幅为10%")\n'
          'else:\n'
          '    print("工资涨幅为15%")'),
    434: ('partcount = int(input())\n'
          'electric = int(input())\n'
          'count = 0\n'
          'while count < partcount:\n'
          '    count += 1\n'
          '    print("已加工零件个数:", count)\n'
          '    if(electric):\n'
          '        print("停电了，停止加工")\n'
          '        break'),
}

ANSWER1_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "answer1")

EXAM_ANSWERS = {
    435: [
        {"qnum": 1, "type": "multichoice", "answer": "C"},
        {"qnum": 2, "type": "multichoice", "answer": "逗号"},
        {"qnum": 3, "type": "multichoice", "answer": "[0,1,2,3,4,5]"},
        {"qnum": 4, "type": "multichoice", "answer": "utf-8"},
        {"qnum": 5, "type": "multichoice", "answer": "复制文件"},
    ],
    437: [
        {"qnum": 1, "type": "essay", "answer": "print(int(5.20))\nprint(int(-5.20))\nprint(int(5.60))\nprint(int(-5.60))", "html": "<p>print(int(5.20))<br>print(int(-5.20))<br>print(int(5.60))<br>print(int(-5.60))</p>"},
        {"qnum": 2, "type": "essay", "answer": "print('welcome to this world')", "html": "<p>print('welcome to this world')</p>"},
        {"qnum": 3, "type": "essay", "answer": "print(\"welcome to this world\")\nmsg = \"welcome to this world\"\nprint(msg)", "html": "<p>print(\"welcome to this world\")<br>msg = \"welcome to this world\"<br>print(msg)</p>"},
        {"qnum": 4, "type": "essay", "answer": "for i in range(1, 10):\n    for j in range(1, i+1):\n        print(f'{j}*{i}={i*j}', end='\\t')\n    print()", "html": "<p>for i in range(1, 10):<br>    for j in range(1, i+1):<br>        print(f'{j}*{i}={i*j}', end='\\t')<br>    print()</p>"},
        {"qnum": 5, "type": "essay", "answer": "lst = [5,8,-7,4,6,2,-3,0]\nmax_val = max(lst)\nmin_val = min(lst)\nlst.remove(min_val)\nlst = [abs(x) for x in lst]\nprint(max_val)\nprint(lst)", "html": "<p>lst = [5,8,-7,4,6,2,-3,0]<br>max_val = max(lst)<br>min_val = min(lst)<br>lst.remove(min_val)<br>lst = [abs(x) for x in lst]<br>print(max_val)<br>print(lst)</p>"},
        {"qnum": 6, "type": "essay", "answer": "from sklearn import preprocessing\nimport pandas as pd\niris = pd.read_csv('iris.csv')\nmin_max_scaler = preprocessing.MinMaxScaler()\nirist_scaled = min_max_scaler.fit_transform(iris.iloc[:,:-1])\nprint(irist_scaled)", "html": "<p>from sklearn import preprocessing<br>import pandas as pd<br>iris = pd.read_csv('iris.csv')<br>min_max_scaler = preprocessing.MinMaxScaler()<br>irist_scaled = min_max_scaler.fit_transform(iris.iloc[:,:-1])<br>print(irist_scaled)</p>"},
        {"qnum": 7, "type": "essay", "answer": "import re\nwith open('walden.txt', 'r', encoding='utf-8') as f:\n    text = f.read()\nwords = re.findall(r'\\b\\w+\\b', text.lower())\nword_count = {}\nfor w in words:\n    word_count[w] = word_count.get(w, 0) + 1\nsorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)\nfor w, c in sorted_words[:10]:\n    print(f'{w}: {c}')", "html": "<p>import re<br>with open('walden.txt', 'r', encoding='utf-8') as f:<br>    text = f.read()<br>words = re.findall(r'\\b\\w+\\b', text.lower())<br>word_count = {}<br>for w in words:<br>    word_count[w] = word_count.get(w, 0) + 1<br>sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)<br>for w, c in sorted_words[:10]:<br>    print(f'{w}: {c}')</p>"},
        {"qnum": 8, "type": "multichoice", "answer": "复制文件"},
        {"qnum": 9, "type": "multichoice", "answer": "Letter[-4:-1:-1]"},
        {"qnum": 10, "type": "multichoice", "answer": "一个语句多行书写时直接回车即可"},
    ],
    440: [
        {"qnum": 1, "type": "multichoice", "answer": "python"},
        {"qnum": 2, "type": "multichoice", "answer": "RStudio"},
        {"qnum": 3, "type": "multichoice", "answer": "收费使用"},
        {"qnum": 4, "type": "essay", "answer": "print('welcome to this world')", "html": "<p>print('welcome to this world')</p>"},
        {"qnum": 5, "type": "essay", "answer": "print(\"welcome to this world\")\nmsg = \"welcome to this world\"\nprint(msg)", "html": "<p>print(\"welcome to this world\")<br>msg = \"welcome to this world\"<br>print(msg)</p>"},
    ],
    441: [
        {"qnum": 1, "type": "multichoice", "answer": "一个语句多行书写时直接回车即可"},
        {"qnum": 2, "type": "multichoice", "answer": "22"},
        {"qnum": 3, "type": "multichoice", "answer": "4"},
        {"qnum": 4, "type": "multichoice", "answer": "**"},
        {"qnum": 5, "type": "multichoice", "answer": "//"},
        {"qnum": 6, "type": "multichoice", "answer": "在第三行声明有效"},
        {"qnum": 7, "type": "multichoice", "answer": "numvalue=10"},
        {"qnum": 8, "type": "multichoice", "answer": "“ Life is short, ” 2 * “you need Python.”"},
        {"qnum": 9, "type": "multichoice", "answer": "\"What's happened to you?\""},
        {"qnum": 10, "type": "multichoice", "answer": "标识符不区分大小写"},
        {"qnum": 11, "type": "essay", "answer": "print(int(5.20))\nprint(int(-5.20))\nprint(int(5.60))\nprint(int(-5.60))", "html": "<p>print(int(5.20))<br>print(int(-5.20))<br>print(int(5.60))<br>print(int(-5.60))</p>"},
        {"qnum": 12, "type": "essay", "answer": "Bet = 6\nresult1 = 1 < Bet < 20\nresult2 = Bet < 10 or Bet > 20\nprint(result1, result2)", "html": "<p>Bet = 6<br>result1 = 1 &lt; Bet &lt; 20<br>result2 = Bet &lt; 10 or Bet &gt; 20<br>print(result1, result2)</p>"},
    ],
    442: [
        {"qnum": 1, "type": "multichoice", "answer": "Letter[-4:-1:-1]"},
        {"qnum": 2, "type": "multichoice", "answer": "集合（set类型）"},
        {"qnum": 3, "type": "multichoice", "answer": "Tuple1+Tuple2"},
        {"qnum": 4, "type": "multichoice", "answer": "Tuple.copy()"},
        {"qnum": 5, "type": "multichoice", "answer": "names.append('Helen','Mary')"},
        {"qnum": 6, "type": "multichoice", "answer": "异或集"},
        {"qnum": 7, "type": "multichoice", "answer": "2"},
        {"qnum": 8, "type": "multichoice", "answer": "{2:'two',3:'One',1:'one'}"},
        {"qnum": 9, "type": "multichoice", "answer": "可变类型"},
        {"qnum": 10, "type": "multichoice", "answer": "A^B"},
        {"qnum": 11, "type": "essay", "answer": "lst = [5,8,-7,4,6,2,-3,0]\nmax_val = max(lst)\nmin_val = min(lst)\nlst.remove(min_val)\nlst = [abs(x) for x in lst]\nprint(max_val)\nprint(lst)", "html": "<p>lst = [5,8,-7,4,6,2,-3,0]<br>max_val = max(lst)<br>min_val = min(lst)<br>lst.remove(min_val)<br>lst = [abs(x) for x in lst]<br>print(max_val)<br>print(lst)</p>"},
        {"qnum": 12, "type": "essay", "answer": "birthday = {'小明': '4月1日', '小红': '1月2日', '老王': '4月1日', '小强': '9月10日'}\nprint(birthday['小明'])\nbirthday['小明'] = '5月1日'\ndel birthday['老王']\nbirthday['小王'] = '10月1日'\nprint(birthday)", "html": "<p>birthday = {'小明': '4月1日', '小红': '1月2日', '老王': '4月1日', '小强': '9月10日'}<br>print(birthday['小明'])<br>birthday['小明'] = '5月1日'<br>del birthday['老王']<br>birthday['小王'] = '10月1日'<br>print(birthday)</p>"},
    ],
    443: [
        {"qnum": 1, "type": "multichoice", "answer": "[0,1,2,3,4,5]"},
        {"qnum": 2, "type": "multichoice", "answer": "elif"},
        {"qnum": 3, "type": "multichoice", "answer": "else语句和while循环语句一起使用，则当条件变为False时，则执行else语句。；else语句和for循环语句一起使用，else语句块只在for循环正常终止时执行。"},
        {"qnum": 4, "type": "multichoice", "answer": "[j for j in range(0,3)]"},
        {"qnum": 5, "type": "multichoice", "answer": "[6,7,8]"},
        {"qnum": 6, "type": "multichoice", "answer": "[]"},
        {"qnum": 7, "type": "multichoice", "answer": "continue"},
        {"qnum": 8, "type": "multichoice", "answer": "布尔值"},
        {"qnum": 9, "type": "multichoice", "answer": "break"},
        {"qnum": 10, "type": "multichoice", "answer": "[4,6,8,10,12]"},
        {"qnum": 11, "type": "essay", "answer": "for i in range(1, 10):\n    for j in range(1, i+1):\n        print(f'{j}*{i}={i*j}', end='\\t')\n    print()", "html": "<p>for i in range(1, 10):<br>    for j in range(1, i+1):<br>        print(f'{j}*{i}={i*j}', end='\\t')<br>    print()</p>"},
        {"qnum": 12, "type": "essay", "answer": "# 打印42图形\nfor i in range(7):\n    row = ''\n    for j in range(7):\n        if i == 0 or i == 6 or i == 3 or (j == 0 and i < 4) or (j == 6 and i > 3):\n            row += '* '\n        else:\n            row += '  '\n    print(row)", "html": "<p># 打印42图形<br>for i in range(7):<br>    row = ''<br>    for j in range(7):<br>        if i == 0 or i == 6 or i == 3 or (j == 0 and i &lt; 4) or (j == 6 and i &gt; 3):<br>            row += '* '<br>        else:<br>            row += '  '<br>    print(row)</p>"},
    ],
    444: [
        {"qnum": 1, "type": "multichoice", "answer": "sort函数"},
        {"qnum": 2, "type": "multichoice", "answer": "lambda表达式解释性良好"},
        {"qnum": 3, "type": "multichoice", "answer": "局部变量可以在外部被调用"},
        {"qnum": 4, "type": "multichoice", "answer": "import Numpy"},
        {"qnum": 5, "type": "multichoice", "answer": "interest(day=2,3000,0.05)"},
        {"qnum": 6, "type": "multichoice", "answer": "元组"},
        {"qnum": 7, "type": "multichoice", "answer": "字典"},
        {"qnum": 8, "type": "multichoice", "answer": "4个空格"},
        {"qnum": 9, "type": "essay", "answer": "import re\nwith open('walden.txt', 'r', encoding='utf-8') as f:\n    text = f.read()\nwords = re.findall(r'\\b\\w+\\b', text.lower())\nword_count = {}\nfor w in words:\n    word_count[w] = word_count.get(w, 0) + 1\nsorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)\nfor w, c in sorted_words[:10]:\n    print(f'{w}: {c}')", "html": "<p>import re<br>with open('walden.txt', 'r', encoding='utf-8') as f:<br>    text = f.read()<br>words = re.findall(r'\\b\\w+\\b', text.lower())<br>word_count = {}<br>for w in words:<br>    word_count[w] = word_count.get(w, 0) + 1<br>sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)<br>for w, c in sorted_words[:10]:<br>    print(f'{w}: {c}')</p>"},
    ],
    445: [
        {"qnum": 1, "type": "multichoice", "answer": "C"},
        {"qnum": 2, "type": "multichoice", "answer": "__call__可以进行赋值"},
        {"qnum": 3, "type": "multichoice", "answer": "open()"},
        {"qnum": 4, "type": "multichoice", "answer": "作为一种建模技术没有很好的定义自己的适用范围"},
        {"qnum": 5, "type": "multichoice", "answer": "self可有可无，也无所谓它的参数位置"},
        {"qnum": 6, "type": "multichoice", "answer": "私有化之后外部就不能访问"},
        {"qnum": 7, "type": "multichoice", "answer": "(file for file in os.listdir('/var/log') if file.endswith('.log'))"},
        {"qnum": 8, "type": "multichoice", "answer": "Smautalk"},
        {"qnum": 9, "type": "multichoice", "answer": "iter函数"},
        {"qnum": 10, "type": "multichoice", "answer": "__getName函数"},
        {"qnum": 11, "type": "essay", "answer": "class Student:\n    def __init__(self, name, age, chinese, math, english):\n        self.name = name\n        self.age = age\n        self.course = {'chinese': chinese, 'math': math, 'english': english}\n    \n    def get_name(self):\n        return self.name\n    \n    def get_age(self):\n        return self.age\n    \n    def get_course(self):\n        return max(self.course, key=self.course.get)\n\nstu = Student('小明', 18, 85, 92, 88)\nprint(stu.get_name())\nprint(stu.get_age())\nprint(stu.get_course())", "html": "<p>class Student:<br>    def __init__(self, name, age, chinese, math, english):<br>        self.name = name<br>        self.age = age<br>        self.course = {'chinese': chinese, 'math': math, 'english': english}<br>    <br>    def get_name(self):<br>        return self.name<br>    <br>    def get_age(self):<br>        return self.age<br>    <br>    def get_course(self):<br>        return max(self.course, key=self.course.get)</p><p>stu = Student('小明', 18, 85, 92, 88)<br>print(stu.get_name())<br>print(stu.get_age())<br>print(stu.get_course())</p>"},
    ],
    446: [
        {"qnum": 1, "type": "multichoice", "answer": "逗号"},
        {"qnum": 2, "type": "multichoice", "answer": "utf-8"},
        {"qnum": 3, "type": "multichoice", "answer": "复制文件"},
        {"qnum": 4, "type": "multichoice", "answer": "//"},
        {"qnum": 5, "type": "multichoice", "answer": "创建文件夹"},
        {"qnum": 6, "type": "multichoice", "answer": "a+"},
        {"qnum": 7, "type": "multichoice", "answer": "dot"},
        {"qnum": 8, "type": "multichoice", "answer": "Read"},
        {"qnum": 9, "type": "multichoice", "answer": "字符型"},
        {"qnum": 10, "type": "multichoice", "answer": "列表"},
        {"qnum": 11, "type": "essay", "answer": "from sklearn import preprocessing\nimport pandas as pd\niris = pd.read_csv('iris.csv')\nmin_max_scaler = preprocessing.MinMaxScaler()\nirist_scaled = min_max_scaler.fit_transform(iris.iloc[:,:-1])\nprint(irist_scaled)", "html": "<p>from sklearn import preprocessing<br>import pandas as pd<br>iris = pd.read_csv('iris.csv')<br>min_max_scaler = preprocessing.MinMaxScaler()<br>irist_scaled = min_max_scaler.fit_transform(iris.iloc[:,:-1])<br>print(irist_scaled)</p>"},
        {"qnum": 12, "type": "essay", "answer": "import os, shutil\nsrc_dir = os.getcwd()\ndst_dir = os.path.join(src_dir, 'my_python')\nos.makedirs(dst_dir, exist_ok=True)\nfor f in os.listdir(src_dir):\n    if f.endswith('.py'):\n        shutil.copy(os.path.join(src_dir, f), os.path.join(dst_dir, f))\nshutil.make_archive('my_python', 'zip', dst_dir)\nprint('完成')", "html": "<p>import os, shutil<br>src_dir = os.getcwd()<br>dst_dir = os.path.join(src_dir, 'my_python')<br>os.makedirs(dst_dir, exist_ok=True)<br>for f in os.listdir(src_dir):<br>    if f.endswith('.py'):<br>        shutil.copy(os.path.join(src_dir, f), os.path.join(dst_dir, f))<br>shutil.make_archive('my_python', 'zip', dst_dir)<br>print('完成')</p>"},
    ],
}

ANSWER_387 = '''my_list = [1, 2, 3, 4, 5]
print("初始列表:", my_list)
my_list.append(6)
print("增加元素后:", my_list)
my_list.remove(3)
print("删除元素后:", my_list)
my_list[0] = 10
print("修改元素后:", my_list)
index = my_list.index(4)
print("元素4的索引:", index)
'''


def generate_all(callback=None):
    os.makedirs(ANSWER_DIR, exist_ok=True)
    total = len(ANSWERS) + 1
    count = 0

    for assign_id, code in ANSWERS.items():
        filename = f"{assign_id}_answer.py"
        filepath = os.path.join(ANSWER_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        count += 1
        if callback:
            callback(count, total)

    filepath = os.path.join(ANSWER_DIR, "387_answer.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(ANSWER_387)
    count += 1
    if callback:
        callback(count, total)

    return count


def generate_selected(ids, callback=None):
    """只生成指定 ID 的答案文件"""
    os.makedirs(ANSWER_DIR, exist_ok=True)
    total = len(ids)
    count = 0
    for assign_id in ids:
        code = ANSWERS.get(assign_id)
        if code is None:
            if callback:
                callback(count + 1, total)
            count += 1
            continue
        filename = f"{assign_id}_answer.py"
        filepath = os.path.join(ANSWER_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        count += 1
        if callback:
            callback(count, total)
    return count


def generate_exam_answers(ids, callback=None):
    """生成考试答案到 answer1/_exam_answers.json 和单个 .py 文件"""
    os.makedirs(ANSWER1_DIR, exist_ok=True)
    total = len(ids)
    count = 0
    all_data = {}
    for exam_id in ids:
        items = EXAM_ANSWERS.get(exam_id)
        if not items:
            all_data[str(exam_id)] = []
            count += 1
            if callback:
                callback(count, total)
            continue
        all_data[str(exam_id)] = items
        py_lines = [f"# -*- coding: utf-8 -*-", f"# 考试 ID: {exam_id}"]
        for q in items:
            py_lines.append(f"# Q{q['qnum']}: {q['answer']}")
        py_path = os.path.join(ANSWER1_DIR, f"{exam_id}_answer.py")
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("\n".join(py_lines))
        count += 1
        if callback:
            callback(count, total)
    json_path = os.path.join(ANSWER1_DIR, "_exam_answers.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    return count
