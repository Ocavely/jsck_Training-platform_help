import os

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
