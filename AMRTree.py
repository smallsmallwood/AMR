import re
import copy
import argparse
import sys
sys.setrecursionlimit(10000)
from itertools import groupby
from operator import itemgetter
from collections import defaultdict
from itertools import combinations
import copy
import threading

class AMRTree:
    class AMRNode:
        def __init__(self, id, name, virtual=False, isattr=False):
            self.id = id
            self.name = name
            self.child = []
            self.father = []
            self.graph = False
            self.virtual = virtual
            self.range = None
            self.isvisited = False
            self.iscalculated = False
            self.preorder_index = None
            self.isattr = isattr

            pass

        def get_id(self):
            pattern_id = re.compile(r'(?<=x)[0-9_]+')
            ids = []
            for e in pattern_id.findall(self.id):
                tmp = [s for s in e.split("_") if s != '']
                if len(tmp) == 1:
                    ids.append(float(tmp[0]))
                    continue
                a = tmp.pop(0)
                for b in tmp:
                    ids.append(float(a)+float(b)/100)
            return ids

    def __init__(self, id, snt, amr):
        self.id = id
        self.snt = snt
        self.word_count = self.__word_count(self.snt)
        self.amr = amr
        #句子是否存在环
        self.circle = False
        # 为AMR文本形式建立AMR树结构
        self.amrtree = self.__build_tree(self.amr)
        # 为每棵树节点的preorder_index设置index
        self.__cal_index()
        self.__cal_range(self.amrtree)

        pass

    def __cal_index(self):

        def __preorder_index(node):
            nonlocal __index
            node.preorder_index = __index
            __index += 1
            for child in node.child:
                if child.preorder_index is None:
                    __preorder_index(child)
        __index = 0
        __preorder_index(self.amrtree)

    def __cal_range(self, amrnode):
        idmax = -1
        idmin = 9999
        amrnode.isvisited = True
        id = amrnode.get_id()
        for child in amrnode.child:
            if child.isvisited == True:
                if child.iscalculated == True:
                    range = child.range
                if child.iscalculated == False:
                    continue
            if child.isvisited == False:
                range = self.__cal_range(child)
            if child.graph == True:
                continue
            if idmax < range[0]:
                idmax = range[0]
            if idmin > range[1]:
                idmin = range[1]
        if amrnode.virtual == False:
            idmax = max([idmax, max(id)+0.0001])
            idmin = min([idmin, min(id)-0.0001])
        amrnode.range = (idmax, idmin)
        amrnode.iscalculated = True
        return amrnode.range

    def __build_tree(self, amr): #解析AMR
        char_queue = copy.deepcopy(amr)
        Head = self.AMRNode('x0','Head')
        node_stack = []
        node_stack.append(Head)

        node_all = []

        def create_node(id, name, node_set = node_all, isattr = False):
            pattern_id = re.compile(r'(?<=x)[0-9]+')
            id_int = int(pattern_id.findall(id)[0])
            new_node = None
            if id_int > self.word_count:
                new_node = self.AMRNode(id,name,True,isattr)
            else:
                new_node = self.AMRNode(id,name,False,isattr)
            if isattr == True:
                return new_node
            for node in node_set:
                if new_node.id == node.id:
                    self.circle = True
                    node.graph = True
                    return node
            node_set.append(new_node)
            return new_node
        isegde = False
        while len(char_queue) > 0:
            char = char_queue.pop(0)
            if char == '(':
                id = char_queue.pop(0)
                # if id=='x21':
                #     a=1
                p = char_queue.pop(0)
                if p != '/':
                    return None
                name = char_queue.pop(0)
                new_node = create_node(id, name)
                node_stack[-1].child.append(new_node)
                node_stack.append(new_node)

            elif char == ')':
                node_stack.pop()
            elif char == ':':
                relationship = char_queue.pop(0)
                isegde=True
                pass
            # else:
            #     if isegde == True:
            #         tmp = char.split('/')
            #         if len(tmp) != 2:
            #             print('error parsing in amr string:', amr)
            #             return None
            #         id = tmp[0]
            #         name = tmp[1]
            #         new_node = create_node(id, name, isattr=True)
            #         node_stack[-1].child.append(new_node)
            #     else:
            #         print('error parsing in amr string:', amr)
            #         return None
        return Head.child[0]

    def __word_count(self, snt):
        return len(snt.split())-2



def mysplit(s, p):
    result = []
    w = ''
    for c in s:
        if c not in p:
            w += c
        else:
            result.append(w)
            result.append(c)
            w = ''
    if w != '':
        result.append(w)
    return result

def split_amr(s):
    result = mysplit(s,'(): \n')
    result = [e for e in result if e != '' and e != ' ' and e != '\n']
    return result

def create_AMRtree(amr):
    tmp2 = amr.split('\n', 3)
    if len(tmp2) < 4:
        return None
    id = tmp2[0]
    print(id)
    snt = tmp2[1]
    amr = split_amr(tmp2[3])
    return AMRTree(id, snt, amr)

def cal_cross_range(range1, range2):
    return min([range1[0], range2[0]])-max([range1[1], range2[1]])

def range_cross(range1, range2):
    if min([range1[0], range2[0]])>max([range1[1], range2[1]]):
        return True

def find_cross_root(amrnode):
    num = len(amrnode.child)
    for i in range(num):
        child1 = amrnode.child[i]
        if child1.graph == True: continue
        if range_cross(child1.range, (max(amrnode.get_id())+0.0001,min(amrnode.get_id())-0.0001)):
            yield ('pc', amrnode, child1)
        for j in range(i+1,num):
            child2 = amrnode.child[j]
            if child2.graph == True: continue
            if range_cross(child1.range, child2.range):
                yield ('cc', child1, child2)
        for r in find_cross_root(child1): yield r

def find_cross_single_pc(fg, n1, n2):
    idmax = max(n1.get_id()) + 0.1
    idmin = min(n1.get_id()) - 0.1
    flag = False
    for child in n2.child:
        if range_cross(child.range, (idmax, idmin)):
            flag = True
            for r in find_cross_single_pc(fg, n1, child): yield r
    if flag == False:
        yield (fg, n1, n2)

def find_cross_single_cc_right_first(fg, n1, n2, f = False):
    flag = False
    for child1 in n2.child:
        if range_cross(child1.range, n1.range):
            flag = True
            for r in find_cross_single_cc_right_first(fg, n1, child1): yield r
    if flag == False and f == False:
        for r in find_cross_single_cc_right_first(fg, n2, n1, True): yield r
    if flag == False and f == True:
        yield (fg, n1, n2)

def find_cross_single_cc(fg, n1, n2, f = False):
    flag = False
    for child1 in n1.child:
        if range_cross(child1.range, n2.range):
            flag = True
            for r in find_cross_single_cc(fg, child1, n2): yield r
    if flag == False and f == False:
        for r in find_cross_single_cc(fg, n2, n1, True): yield r
    if flag == False and f == True:
        yield (fg, n1, n2)

def find_cross(amrnode):
    allcross = find_cross_root(amrnode)
    for tu in allcross:
        if isinstance(tu, tuple):
            fg = tu[0]
            n1 = tu[1]
            n2 = tu[2]
            if fg == 'pc':
                for r in find_cross_single_pc(fg, n1, n2):
                    yield r
            if fg == 'cc':
                for r in find_cross_single_cc(fg, n1, n2):
                    yield r
                # for r in find_cross_single_cc_right_first(fg, n1, n2):
                #     yield r
        else:
            yield None

def find_cross_edge(cross):
    # cross = find_cross(AMR.amrtree)
    # for fg, n1, n2 in cross:
    fg = cross[0]
    n1 = cross[1]
    n2 = cross[2]
    if fg is 'pc':
        for child in n2.child:
            if range_cross((max(n1.get_id())+0.0001,min(n1.get_id())-0.0001), (max([child.range[0],max(n2.get_id())+0.0001]),min([child.range[1],min(n2.get_id())-0.0001]))):
                yield (n2, child)
    elif fg is 'cc':
        for child in n2.child:
            if range_cross(n1.range, (max([child.range[0],max(n2.get_id())+0.0001]),min([child.range[1],min(n2.get_id())-0.0001]))):
                yield (n2, child)
        for child in n1.child:
            if range_cross(n2.range, (max([child.range[0],max(n1.get_id())+0.0001]),min([child.range[1],min(n1.get_id())-0.0001]))):
                yield (n1, child)

def combine_edge(cross):
    for c in cross:
        edge = find_cross_edge(c)
        r = c
        n1 = c[1]
        n2 = c[2]
        for e in edge:
            ncp = e[0]
            if n1 is ncp:
                r = ('ce', n2, e, c)
            elif n2 is ncp:
                r = ('ce', n1, e, c)
        yield r

def combine_edge_single(c):
    edge = find_cross_edge(c)
    fg = c[0]
    n1 = c[1]
    n2 = c[2]
    for e in edge:
        ncp = e[0]
        if n1 is ncp:
            yield (fg, n2, e)
        elif n2 is ncp:
            yield (fg, n1, e)

def get_nonpro_node_single(single_combined_cross):
    n1 = single_combined_cross[1]
    n2 = single_combined_cross[2][1]
    if n1.preorder_index > n2.preorder_index:
        return n1
    else:
        return n2

def get_nonpro_node(combined_cross):
    for single_combined_cross in combined_cross:
        if single_combined_cross[0] is 'ce':
            n1 = single_combined_cross[1]
            n2 = single_combined_cross[2][1]
            if n1.preorder_index > n2.preorder_index:
                yield (n1, single_combined_cross[3])
            else:
                yield (n2, single_combined_cross[3], single_combined_cross)
        elif single_combined_cross[0] is 'pc':
            yield (single_combined_cross[2], single_combined_cross)
        elif single_combined_cross[0] is 'cc':
            n1 = single_combined_cross[1]
            n2 = single_combined_cross[2]
            if n1.preorder_index > n2.preorder_index:
                yield (n1,single_combined_cross)
            else:
                yield (n2,single_combined_cross)

def get_cross(amrtree):
    result = dict()
    cross = find_cross(amrtree)
    cross = list(cross)
    result['cross'] = cross
    combined_cross = combine_edge(cross)
    combined_cross = list(combined_cross)
    result['combined'] = combined_cross
    cross_node = get_nonpro_node(combined_cross)
    cross_node = sorted(cross_node, key=lambda x: x[0].preorder_index)
    result['nodecross'] = cross_node
    node_group = groupby(cross_node, itemgetter(0))
    result['nodegroup'] = node_group
    # for n, m in node_group:
    #     print(n.id, n.name)
    #     for nc in m:
    #         c = nc[1]
    #         print('----', c[0], c[1].id, c[1].name, c[2].id, c[2].name)
    return result

''' 是否需要
def distinct(combined_cross):
    for n, m in groupby(combined_cross, itemgetter(1)):
        print(n)
        print(list(m))
    for n, m in groupby(combined_cross, itemgetter(2)):
        print(n)
        print(list(m))
'''

def iscircle1(amrnode):
    node_list = []
    def depth_search(amrnode):
        if amrnode in node_list:
            return True
        node_list.append(amrnode)
        flag = False
        for child in amrnode.child:
            if child.isattr == True:
                continue
            flag = flag or depth_search(child)
        node_list.remove(amrnode)
        return flag
    return depth_search(amrnode)

def iscircle(amrnode):
    node_list = []
    def depth_search(amrnode):
        if amrnode in node_list:
            return True
        node_list.append(amrnode)
        flag = False
        for child in amrnode.child:
            if child.isattr == True:
                continue
            flag = flag or depth_search(child)

        return flag
    return depth_search(amrnode)

def readfile(filename, encoding = 'utf8'):
    pattern_edge = re.compile(r':[a-z0-9_\-]+\(\S*?\)')
    pattern_id = re.compile(r'# ::id')
    pattern_amr = re.compile(r'# ::id [\s\S]+?(?=\n\n)')
    file = open(filename, mode='r', encoding=encoding)
    str = file.read()
    str = pattern_id.sub('\n# ::id', str)
    str = pattern_edge.sub(':edge', str)
    AMRs = pattern_amr.findall(str)
    return AMRs

def get_all_amr(filename):
    AMRs = readfile(filename_amr_input)
    AMR_ALL = []
    for tmp in AMRs:
        if tmp == '':
            continue
        try:
            new_amr = create_AMRtree(tmp)
            if new_amr == None:
                print('None')
                continue
            AMR_ALL.append(new_amr)
        except Exception as e:
            print(e)
    return AMR_ALL




#判断amr中是否存在环
def isgraph(amrnode):
    def deepsearch(amrnode):
        if amrnode.child == []:
            return False
        Flag = False
        for child in amrnode.child:
            Flag = child.graph or Flag
            flag = isgraph(child)
        return Flag or flag
    return deepsearch(amrnode)

def findgraphnode(amrnode):
    graphnode = []

    def deepsearch(amrnode):
        if amrnode.graph:
            if amrnode not in graphnode:
                graphnode.append(amrnode)
        for node in amrnode.child:
            deepsearch(node)

    deepsearch(amrnode)
    return graphnode

def findAllPath(start,end, path=[]):
    path = path+[start]
    if start == end:
        return [path]
    paths = []
    for node in start.child:
        newpaths = findAllPath(node, end, path)
        for new in newpaths:
            paths.append(new)
    return paths

def getgraphpath(AMR):
    amrnode = AMR.amrtree
    graphnode = findgraphnode(amrnode)
    nodepaths = {}
    for node in graphnode:
        if node.graph:
            paths = findAllPath(amrnode, node)
            nodepaths[node.id] = paths
        else:
            print("%s NOT GRAPH" % AMR.id)

    return nodepaths

def iszero(AMR):
    name = ["and", "causation", "condition", "contrast", "temporal", "or", "concession", "orx", "progression"]
    nodepaths = getgraphpath(AMR)
    flag = False
    for id in nodepaths:
        paths = nodepaths[id]
        num_paths = len(paths)
        assert num_paths >= 2
        poss_combi = combinations(paths, 2)
        for combi_ in poss_combi:
            combi = copy.deepcopy(combi_)
            combi[0].pop()
            combi[0].reverse()
            path1 = combi[0]
            combi[1].pop()
            combi[1].reverse()
            path2 = combi[1]
            for node in path2:
                if node in path1:
                    if node.name in name:
                        flag = True
                    break
            if flag:
                break
    return flag


filename_amr_input = 'amr小学语文全.txt'
# filename_amr_input = 'test.txt'
# filename_cross_output = 'ctb/ctb_train_cross.txt'
# filename_circle_output = 'ctb/ctb_train_circle.txt'
# filename_stat_output = 'ctb/ctb_train_stat.txt'
filename_cross_output = filename_amr_input + '.cross'
filename_circle_output = filename_amr_input + '.circle'
filename_stat_output = filename_amr_input + '.stat'
filename_graph_output = filename_amr_input + '.graph'


def write_possible_zero(filename_amr_input):
    all = []
    error = []
    AMR_ALL = get_all_amr(filename_amr_input)
    print("++++++++++++++++++++++++++++++++++++++++++++++")
    n = 0
    for AMR in AMR_ALL:
        try:
            if AMR.circle:
                if iszero(AMR):
                    all.append(AMR.id)
        except:
            error.append(AMR.id)
            n += 1
    print("带环的AMR:"+str(n))
    print("+++++++++++++++++++++++++++++++++++++++++++++++")
    print("在不同子句的补全AMR:"+str(len(all)))

    with open("circle_zero.txt", "w") as filename:
        for id in all:
            filename.write(id+'\n')

def write_amr(ids,filename_amr_imput):
    pattern_amr = re.compile(r'# ::id [\s\S]+?(?=\n\n)')
    re_id = re.compile(r"(?<=# ::id export_amr.)\d*?(?= ::)")
    pattern_id = re.compile(r'# ::id')
    file = open(filename_amr_input, mode='r')
    str = file.read()
    str = pattern_id.sub('\n# ::id', str)
    AMRs = pattern_amr.findall(str)
    zero_amrs = []
    for amr in AMRs:
        id = re.findall(re_id, amr)[0]
        if id in ids:
            ids.remove(id)
            zero_amrs.append(amr)
    _ = list(set(ids)-set(zero_amrs))
    with open("zero_amr.txt", "w") as filename:
        for amr in zero_amrs:
            filename.write(amr+"\n\n")



if __name__ == "__main__":
    # write_possible_zero(filename_amr_input)
    gold = []
    with open("gold", "r") as filename:
        lines = filename.readlines()
        for id in lines:
            gold.append(id.strip("\n"))
    poss_gold = []
    with open("circle_zero.txt", "r") as filename:
        lines = filename.readlines()
        for line in lines:
            poss_gold.append(line.strip("\n"))

    re_id = re.compile(r"(?<=# ::id export_amr.)\d*?(?= ::)")
    ids = [_ for line in poss_gold for _ in re.findall(re_id, line)]
    intersection = list(set(ids)&set(gold))
    ids_gold = list(set(ids)-set(gold))
    gold_ids = list(set(gold)-set(ids))
    write_amr(intersection, filename_amr_input)


# if __name__ == '__main3__':
#     # argparser = argparse.ArgumentParser(description='Process some integers.')
#     # argparser.add_argument("-f", "--file", help="File Name", require=True)
#     # try:
#     #     args = argparser.parse_args()
#     # except:
#     #     argparser.error("Invalid arguments")
#     #     sys.exit(0)
#     # filename_amr_input = arg.file
#     AMR_ALL = get_all_amr(filename_amr_input)
#     file_cross = open(filename_cross_output, mode='w', encoding='utf8')
#     file_circle = open(filename_circle_output, mode='w', encoding='utf8')
#
#     pattern_intid = re.compile(r'(?<=_amr\.)[0-9]+')
#     static = defaultdict(int)
#     intid = ''
#     for AMR in AMR_ALL:
#         intid = pattern_intid.findall(AMR.id)[0]
#         print(intid)
#         static[intid] = 1
#         if iscircle(AMR.amrtree) == True:
#             print('Circle')
#             file_circle.write(AMR.id+'\n')
#             continue
#         result = get_cross(AMR.amrtree)
#         if len(result['cross']) > 0:
#             static[intid] = 2
#             file_cross.write(AMR.id+'\n'+AMR.snt+'\n')
#             for n, m in result['nodegroup']:
#                 file_cross.write(n.id + ' ' + n.name + '\n')
#                 for nc in m:
#                     c = nc[1]
#                     file_cross.write('----' + ' '.join([c[0], c[1].id, c[1].name, c[2].id, c[2].name]) + '\n')
#                     if len(nc)>2:
#                         ce = nc[2]
#                         file_cross.write('    ----' + ' '.join([ce[0], ce[1].id, ce[1].name, ce[2][0].id, ce[2][0].name, '===>', ce[2][1].id, ce[2][1].name]) + '\n')
#             file_cross.write('\n\n')
#     file_stat = open(filename_stat_output, mode='w', encoding='utf8')
#     for i in range(int(intid)):
#         intid2 = str(i+1)
#         if static[intid2] == 1:
#             file_stat.write(intid2 + "\t0\n")
#         elif static[intid2] == 2:
#             file_stat.write(intid2 + "\t1\n")
#         else:
#             file_stat.write(intid2 + "未标注\n")

# if __name__ == '__main2__':
#     # pattern_edge = re.compile(r':[a-z0-9_\-]+\(\S*?\)')
#     # file = open('export_amr_wy.txt',mode='r',encoding='utf8')
#     # str = file.read()
#     # file.close()
#     # str = pattern_edge.sub(':edge', str)
#     # pattern_amr = re.compile(r'# ::id [\s\S]+(?=[(\n\n\n)(# ::id )])')
#     # AMRs = pattern_amr.findall(str)
#     # AMRs = str.split('\n\n\n')
#     # AMRs = readfile(filename_amr_input)
#     # AMRs = readfile('amr_test.txt')
#     AMR_ALL = get_all_amr(filename_amr_input)
#     # for tmp in AMRs:
#     #     if tmp == '':
#     #         continue
#     #     try:
#     #         new_amr = create_AMRtree(tmp)
#     #         AMR_ALL.append(new_amr)
#     #     except Exception as e:
#     #         print(e)
#
#     print('读取成功')
#     file_cross = open(filename_cross_output,mode='w',encoding='utf8')
#     file_circle = open(filename_circle_output, mode='w', encoding='utf8')
#     num = 0.0
#     for AMR in AMR_ALL:
#         if iscircle(AMR.amrtree) == True:
#             print('Circle')
#             file_circle.write(AMR.id+'\n')
#             continue
#         cross = find_cross(AMR.amrtree)
#         print(AMR.id)
#         num_cross = 0
#         str = AMR.id + '\n' + AMR.snt + '\n'
#         for c in cross:
#             num_cross += 1
#             print(c[0], c[1].id, c[1].name, c[2].id, c[2].name)
#             edge = find_cross_edge(c)
#             for e in edge:
#                 print('----',e[0].id, e[0].name, e[1].id, e[1].name)
#             str +=  ' '.join([c[0], c[1].id, c[1].name, c[2].id, c[2].name]) + '\n'
#         if num_cross > 0:
#             num+=1
#             file_cross.write(str+'\n')
#         else:
#             print('No Cross')
#     print(num, num/len(AMR_ALL))
#
#
#     # 非投影 环 图
#     #