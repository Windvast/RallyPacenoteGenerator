import requests, json, csv, math
import pandas as pd
from plotnine import *
from time import *

amap_api_url = 'https://restapi.amap.com/v5/direction/driving?'
my_key = 'type your user key here'
origin_loc = '120.070737,31.399807' 
dest_loc = '120.079353,31.383834'
way_point = '120.06821,31.380062'
turn_threshold = 5 #degrees
turn_threshold2 = 25 #degrees
straight_threshold = 50 #meters

request_url = amap_api_url + 'key=' + my_key + '&origin=' + origin_loc + '&destination=' + dest_loc + '&extensions=base' + '&show_fields=polyline' + '&waypoints=' + way_point
response = requests.get(request_url)
response_dic = json.loads(response.text)

'''
with open('amap_response.json','w',encoding='utf-8') as file:
    file.write(json.dumps(response_dic,indent=2,ensure_ascii=False))
'''    
paths = response_dic['route']['paths'][0]['steps']
route_points = []

# flat the coordinates in returned dict
for section in paths:
    polyline = section['polyline']
    polyline = polyline.split(';')
    polyline = [tuple([float(xy) for xy in coor.split(',')]) for coor in polyline]
    route_points += polyline

def project_vector(coord1:tuple, coord2:tuple)->tuple:
    '''
    this function calculates the horizontal and vertical distance between two gps coordinates (longitude, latitude)
    Args:
        coord1: this is a tuple of (longitude1, latitude1) in degrees
        coord2: this is a tuple of (longitude2, latitude2) in degrees
    Return:
        A tuple like (distance_horizontal, distance_vertical), east and north are +, west and south are -, the unit is M
    '''
    lon1 = coord1[0]
    lat1 = coord1[1]
    lon2 = coord2[0]
    lat2 = coord2[1]

    avg_lat = (lat1+lat2)/2
    x_vec = 6367000*math.cos(math.radians(avg_lat))*math.radians(lon2-lon1)
    y_vec = 6367000*math.radians(lat2-lat1)
    return (x_vec, y_vec)

# calculate turn angle and left or right
def calc_turn_angle(coord1:tuple, coord2:tuple)->float:
    '''
    this function calculate the angle between two adjacent vectors, e.g., calc_turn_angle((0,1),(1,0)) returns -90
    Args:
        coord1: this is a tuple of (coor1_x, coor1_y) in meters (with direction)
        coord2: this is a tuple of (coor2_x, coor2_y) in meters (with direction)
    Return:
        A decimal of degree with direction, e.g., -90 means turn square right
    '''
    x1 = coord1[0]
    y1 = coord1[1]
    x2 = coord2[0]
    y2 = coord2[1]
    det = x1*y2 - x2*y1
    turn_direction = 0
    if det < 0:
        turn_direction = -1 # turn right, show right 
    else:
        turn_direction = 1 # turn left, show blue
    turn_angle_deg = math.degrees(math.acos((x1*x2+y1*y2)/(math.sqrt(x1**2+y1**2)*math.sqrt(x2**2+y2**2))))

    return turn_direction * round(turn_angle_deg)

# calculate distance between two point
def get_dist(coor0, coor1):
    return math.sqrt( (coor0[0]-coor1[0])**2 + (coor0[1]-coor1[1])**2 )

# calculate radius of a turn
def get_radius(coor0:tuple, coor1:tuple, coor2:tuple, coor3:tuple):
    '''
    this function calculate the sharpness of a turn based on its entrance and exit points
    Args:
        coor0: the point before coor1
        coor1: point of s->t
        coor2: poitn of t->s
        coor3: the point after coor2
    Return:
        a tuple of the distances between the intersection point
    '''
    #1 get line functions of line1 based on (coor0,coor1) and line2 based on (coor1,coor2)
    line1_A = coor0[1] - coor1[1]
    line2_A = coor2[1] - coor3[1]
    line1_B = coor1[0] - coor0[0]
    line2_B = coor3[0] - coor2[0]
    line1_C = -line1_A*coor1[0] - line1_B*coor1[1]
    line2_C = -line2_A*coor2[0] - line2_B*coor2[1]
    #2 get line1p perpendicular to line1(throgh point coor1)and line2p perpendicular to line2(throgh point coor2)
    line1p_A = line1_B
    line2p_A = line2_B
    line1p_B = -1*line1_A
    line2p_B = -1*line2_A
    line1p_C = -line1p_A*coor1[0] - line1p_B*coor1[1]
    line2p_C = -line2p_A*coor2[0] - line2p_B*coor2[1]
    
    #3 get intersection point coor_its of line1p and line2p
    det   = line1p_A*line2p_B - line1p_B*line2p_A
    det_x = -1*(line1p_C*line2p_B - line1p_B*line2p_C)
    det_y = -1*(line1p_A*line2p_C - line1p_C*line2p_A)
    #4 get distance radius_ext and radius_ent between coor_its and coor1, coor2, respectively
    if det != 0:
        coor_its = (det_x/det, det_y/det)
        radius_ext = get_dist(coor_its,coor1)
        radius_ent = get_dist(coor_its,coor2)
        alternation = 'open' if radius_ext/radius_ent>1.5 else ('tighten' if radius_ent/radius_ext>1.5 else '')
    #5 tackle parallel
    else:
        radius_ent = 1/2 * abs(line1_C-line2_C) / math.sqrt(line1_A**2+line1_B**2)
        alternation = ''
    #6 get 0-6 severity degree    
    if radius_ent <= 14:
        severity_ent = 0
    elif radius_ent <= 20:
        severity_ent = 1
    elif radius_ent <= 29:
        severity_ent = 2
    elif radius_ent <= 41:
        severity_ent = 3
    elif radius_ent <= 65:
        severity_ent = 4
    elif radius_ent <= 110:
        severity_ent = 5
    else:
        severity_ent = 6

    return (severity_ent,alternation)
    
def get_sharp_severity(deg):
    if deg > 171:
        return 0
    elif deg >116:
        return 1
    elif deg > 80:
        return 2
    elif deg > 55:
        return 3
    elif deg > 35:
        return 4
    elif deg >21:
        return 5
    else:
        return 6

# generate sections(vectors) based on route_points, n points so number of sections is n-1
section_vectors = []
for point_i in range(len(route_points)-1):
    vector = project_vector(route_points[point_i],route_points[point_i+1])
    section_vectors.append(vector)
section_vectors = [tup for tup in section_vectors if tup != (0,0)]

# generate actual coordinates based on section vectors

actual_coor = [(0,0)]
for vector_i in range(len(section_vectors)):
    prev_point = actual_coor[-1]
    curr_point = section_vectors[vector_i]
    zipped_tuple = zip(prev_point,curr_point)
    mapped_tuple = tuple(map(sum,zipped_tuple))
    actual_coor.append(mapped_tuple)
# print(actual_coor)

# calculate section distance based on section_vectors, n-1 sections so number of distance is also n-1
section_dist = list(map(lambda coor:math.sqrt(coor[0]**2+coor[1]**2),section_vectors))
# append NaN to the end of section_dist
section_dist.append(None)
# print(section_dist)

# calculate turns based on sections(vectors), points of n, vectors of n-1, turns of n-2
route_turns = []
for turn_i in range(len(section_vectors)-1):
    turn = calc_turn_angle(section_vectors[turn_i],section_vectors[turn_i+1])
    route_turns.append(turn)
# print(route_turns)
# add NaN to the start and end of route_turns
route_turns.insert(0,0)
route_turns.append(0)


# export the 2D list in a csv file
# with open('route.csv','w',newline='') as f:
#     write = csv.writer(f)
#     write.writerows(route_0)

# create pandas DataFrame
df = pd.DataFrame(actual_coor)
df.columns = ['coor_x','coor_y']
df['dist'] = section_dist
df['deg'] = route_turns
df['turn'] = df['deg'].apply(lambda deg: 'left' if deg>turn_threshold else ('right' if deg <-turn_threshold else 'line'))
df['twist'] = ''

# core algorithm
p_s_t = 0 # pointer where a straight becomes a turn
p_t_s = 0 # pointer where a turn becomes a staright
p_c = 1 # pointer of current move
is_turn = 0 # marker of current state
# FSA
list_pacenote = []

while p_c < len(df.index)-1: # drop the last section
    # print(p_c)
    # s->s
	# if it's in a straight and next step is almost linear, keeps driving to next point
    if (is_turn==0 and abs(df.loc[p_c,'deg'])<=turn_threshold) or (is_turn==0 and abs(df.loc[p_c,'deg'])<=turn_threshold2 and abs(df.loc[p_c+1,'deg'])<=turn_threshold): 
        p_c += 1
        continue

    # t->t
    # if it's in turn and next section turns more than turn_threshold deg (same direction), keeps turning
    if is_turn ==1 and df.loc[p_c,'deg']*df.loc[p_c-1,'deg']>0 and abs(df.loc[p_c,'deg'])>turn_threshold and df.loc[p_c,'dist']<=straight_threshold:
        p_c += 1
        continue

    # t->s
    # if there's a long straight section (with same turn direction) after a turn, the turn ends here
    if is_turn==1 and df.loc[p_c,'dist']>straight_threshold:
        p_t_s = p_c
        if p_s_t==p_t_s:
            turn_direction = 'R' if df.loc[p_c,'deg']<0 else 'L'
            turn_deg = get_sharp_severity(df.loc[p_s_t,'deg'])
            list_pacenote.append({'isTurn':1, 'direction':turn_direction, 'radius':turn_deg, 'duration':'Sharp','index':(p_s_t,p_t_s)})
        else:
            turn_direction = 'R' if df.loc[p_c-1,'deg']<0 else 'L' #in case turn in another direction
            turn_radius, turn_alter = get_radius(tuple(df.loc[p_s_t-1,['coor_x','coor_y']]), tuple(df.loc[p_s_t,['coor_x','coor_y']]), tuple(df.loc[p_t_s,['coor_x','coor_y']]), tuple(df.loc[p_t_s+1,['coor_x','coor_y']]))
            turn_deg = 'long' if df.loc[p_s_t:p_t_s-1,'deg'].sum()>=120 else ''
            list_pacenote.append({'isTurn':1,'direction':turn_direction,'radius':turn_radius,'alter':turn_alter, 'duration':turn_deg,'index':(p_s_t,p_t_s)})
        df.loc[p_c,'twist'] += 't->s'
        is_turn = 0
        p_c +=1
        continue

    # t->s s->t
    # if it's in a turn in one direction, then next dot has a turn in another direction
    if is_turn==1 and df.loc[p_c,'deg'] * df.loc[p_c-1,'deg']<-turn_threshold**2:
        p_t_s = p_c-1
        df.loc[p_c-1,'twist'] += 't->s'
        turn_direction = 'R' if df.loc[p_s_t,'deg']<0 else 'L'
        if p_s_t==p_t_s: # this is an sharp turn
            turn_deg = get_sharp_severity(df.loc[p_s_t,'deg'])
            list_pacenote.append({'isTurn':1,'direction':turn_direction,'radius':turn_deg,'duraction':'Sharp','index':(p_s_t,p_t_s)})
        else:
            turn_radius, turn_alter = get_radius(tuple(df.loc[p_s_t-1,['coor_x','coor_y']]), tuple(df.loc[p_s_t,['coor_x','coor_y']]), tuple(df.loc[p_t_s,['coor_x','coor_y']]), tuple(df.loc[p_t_s+1,['coor_x','coor_y']]))
            # turn_alter = 'tighten' if turn_radius[0]/turn_radius[1]<0.75 else ('open' if turn_radius[1]/turn_radius[0]<0.75 else '')
            turn_deg = 'long' if df.loc[p_s_t:p_t_s-1,'deg'].sum()>=120 else ''
            list_pacenote.append({'isTurn':1,'direction':turn_direction,'radius':turn_radius,'alter':turn_alter, 'duration':turn_deg,'index':(p_s_t,p_t_s)})
        p_s_t = p_c
        df.loc[p_c,'twist'] += 's->t'
        p_c +=1
        continue

    # s->t
    # if it's in a straight and next step is a turn, starts to turn
    if (is_turn==0 and abs(df.loc[p_c,'deg'])>turn_threshold and abs(df.loc[p_c+1,'deg'])>turn_threshold) or (is_turn==0 and abs(df.loc[p_c,'deg'])>turn_threshold2):
        p_s_t = p_c
        distance_straight = round(df.loc[p_t_s:p_s_t-1,'dist'].sum()/10)*10
        list_pacenote.append({'isTurn':0,'dist':distance_straight,'index':(p_t_s,p_s_t)})
        is_turn = 1
        df.loc[p_c,'twist'] += 's->t'
        if df.loc[p_c,'dist']<=straight_threshold:
            p_c += 1
            continue

    # t->s
    # a normal end of turn
    if is_turn==1 and abs(df.loc[p_c,'deg'])<=turn_threshold:
        p_t_s = p_c-1
        turn_direction = 'R' if df.loc[p_c-1,'deg']<0 else 'L'
        turn_radius, turn_alter = get_radius(tuple(df.loc[p_s_t-1,['coor_x','coor_y']]), tuple(df.loc[p_s_t,['coor_x','coor_y']]), tuple(df.loc[p_t_s,['coor_x','coor_y']]), tuple(df.loc[p_t_s+1,['coor_x','coor_y']]))
        turn_deg = 'long' if df.loc[p_s_t:p_t_s-1,'deg'].sum()>=120 else ''
        list_pacenote.append({'isTurn':1,'direction':turn_direction,'radius':turn_radius,'alter':turn_alter, 'duration':turn_deg,'index':(p_s_t,p_t_s)})
        df.loc[p_t_s,'twist'] += 't->s'
        is_turn = 0
        p_c += 1
        continue

if is_turn==0:
    distance_straight = round(df.loc[p_t_s:p_c-1,'dist'].sum()/10)*10
    list_pacenote.append({'isTurn':0,'dist':distance_straight,'index':(p_t_s,p_c)})
else:
    p_t_s = p_c
    turn_direction = 'R' if df.loc[p_c-1,'deg']<0 else 'L'
    turn_radius, turn_alter = get_radius(tuple(df.loc[p_s_t-1,['coor_x','coor_y']]), tuple(df.loc[p_s_t,['coor_x','coor_y']]), tuple(df.loc[p_t_s-1,['coor_x','coor_y']]), tuple(df.loc[p_t_s,['coor_x','coor_y']]))
    turn_deg = 'long' if df.loc[p_s_t:p_t_s-1,'deg'].sum()>=120 else ''
    list_pacenote.append({'isTurn':1,'direction':turn_direction,'radius':turn_radius,'alter':turn_alter, 'duration':turn_deg,'index':(p_s_t,p_t_s)})


# draw df, pacenote and ggplot
pd.set_option('display.max_rows', None)
# print(df)
# df.to_csv(r'YourPath\YourFileName')
print(list_pacenote)
'''
g = (ggplot(data=df, mapping=aes(x='coor_x',y='coor_y')) 
+ geom_path()
+ geom_point(data=df, size=0.02) 
+ geom_point(aes(color='turn')) 
+ scale_color_manual({'line':'grey','right':'red','left':'blue'})
+ coord_fixed(ratio=1) 
+ geom_text(aes(label=df.index),size=3,color='white')
)
g.draw(show=True)
'''
# g.save(filename = r'YourPath\YourFileName', height=50, width=50, units = 'cm', dpi=1000)
# print('ggplot successfully generated')
print(strftime('%Y-%m-%d %H:%M:%S',localtime()))