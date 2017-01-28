# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 17:55:44 2017
Pushbrrom bat 
@author: Yun 
"""
import pylab 
import numpy as np
import project_bat as pb 
import bat_visualize as bv
import copy 
import math

"""
*****************
STATUS
*****************
currently mostly work. But sometimes when given some coordinate goals (ex. 45., 9) will arrive at some 
point but not the point i want it to be at 
"""

"""
Define a few path-finding functions for use later
"""

def find_opt_path_DFS(grid, start, end, path, optim, threshold=0.5):
    """
    given a matrix of probabilities, where tiles with probabilities above t
    hreshold are assumed as occupied (obstacles) tiles and otherwise are free. 
    Start is the beginning grid and end is the goal grid. Find optimal path 
    initialize path = [] and optim = None
    Seems a little too slow, but keeping this function here in case I might use it in the future 
    """
    grid_shape = grid.shape
    num_row = grid_shape[0]
    num_col = grid_shape[1]
    path = path + [start] 
    if start == end: 
        return path
    next_step = []
    for i in range(-1,2):
        for j in range(-1,2): 
            ns = start
            a = ns[0] + i
            b = ns[0] + j 
            if a >= 0 and a < num_row and b >= 0 and b < num_col:
                if grid[a, b] < threshold and [a,b] != start:
                    next_step.append([a, b])
    for step in next_step:
        if step not in path:
            if optim == None or len(path) < len(optim):
                newpath = find_opt_path_DFS(grid, step, end, path, optim)
                if newpath != None: 
                    optim = newpath 
    return optim
 
def get_heuristic(grid, start, end, threshold): 
    """
    heuristic for A* search. Basically the matrix that stores the number of steps away 
    from the destination for each tile 
    """ 
    #generate heuristic 
    grid_shape = grid.shape
    num_row = grid_shape[0]
    num_col = grid_shape[1]
    ref = pylab.matrix(grid)
    heuristic = pylab.matrix([[99 for col in range(num_col)] for row in range(num_row)])
    notdone = True
    step = 1
    current = [end[:]]
    ref[end[0], end[1]] = 1
    heuristic[end[0], end[1]] = 0
    while notdone: 
        if start in current: 
            notdone = False 
        else: 
            new = []
            for tile in current: 
                for i in range(-1,2):
                    for j in range(-1,2): 
                        ns = tile
                        a = ns[0] + i
                        b = ns[1] + j 
                        if a >= 0 and a < num_row and b >= 0 and b < num_col:
                            if ref[a, b] < threshold:
                                heuristic[a,b] = step
                                ref[a,b] = 1
                                new.append([a,b])
            current = new
            step += 1
    return heuristic 

def surr_grid_ok(grid, tile, threshold):
    """
    this function is to supplement the A* search as to add an additional requirement
    so that the tiles in a grid cannot by bordered by grids that are above thrershold 
    as a safety measure
    """
    for i in range(-1, 2):
        for j in range(-1, 2):
            try: 
                if grid[tile[0]+i, tile[1]+j] > threshold: 
                    return False
            except IndexError: 
                pass 
    return True 
    
def find_opt_path_As(grid, start, end, threshold): 
    """
    same function as find_opt_path_DFS but instead of implementing a depth first 
    search, implement an A* search for speed
    Basically proceed step by step, always choose the value that has the lower 
    (step number + heuristic number + probability of there being an obstacle) 
    """
    grid_shape = grid.shape
    num_row = grid_shape[0]
    num_col = grid_shape[1]
    ref = pylab.matrix(grid)
    heuristic = get_heuristic(grid, start, end, threshold)
    path = [start]
    current = start[:]
    step = 0
    try:
        while current != end: 
            minval = 99
            best = None
#            for i in range(-1,2):
#                for j in range(-1,2):
            for [i,j] in [[1,0],[0,1],[-1,0],[0,-1]]:              
                ns = current
                a = ns[0] + i
                b = ns[1] + j
                if a >=0 and a < num_row and b>= 0 and b < num_col:
                    if ref[a,b] < threshold:
                        if surr_grid_ok(ref, [a,b], threshold):
                            val = step + heuristic[a,b] + grid[a,b]
                            if val < minval: 
                                best = [a,b]
                                minval = val 
            step += 1
            current = best
            path.append(best)
    except TypeError: 
        return None
    return path 

class Pushbroom(object):
    def __init__(self, min_dist, max_dist, fov, dist_per_que, goal, threshold = 0.5):
        """
        initialize queue to store sensed obstacles 
        goal is given from initial bearing (angle) and distance
        away from the bat
        max dist is max sensing dist and min dist is min sensing dist 
        """
        self.goal = goal #format [angle, distance]
        num_queue = int(max_dist/dist_per_que)*2 + 1
        #Going to initialize bat in the middle of the grid 
        self.num_queue = num_queue
        self.mindist = min_dist
        self.maxdist = max_dist
        self.dist_pq = dist_per_que
        self.obst_queue = pylab.matrix(np.zeros((num_queue, num_queue)))
        self.path = []
        self.fov = fov
        self.goal_index = None
        self.real_goal = False 
        self.threshold = threshold  
        self.bat_tile = [(num_queue - 1)/2, (num_queue - 1)/2]
        self.bat_pos = [0, 0]
        """
        note: intially the goal might not be included in grid beacuse it is too 
        far away, in that case, leave real_goal parameter as false and set goal 
        and goal_index as a tile/point in the general direction towards the real 
        goal. This will be generated in the initialize queue function
        Keep in mind that self.goal has to be updated everytime the queue is to be 
        reinitiated 
        """
    
    def initialize_queue(self, list_obstacles, meas_certainty=0.8):
        """
        add a list (with each entry being a list [degree, distance], with distance being in queue units) of 
        obstacles obeserved initially to the obstacle queue
        """
        num_queue = self.num_queue
        limt = (num_queue - 1)/2 #since the origin is in the center 
        #first perform bat_tile and goal update 
        goal = self.goal 
        rad = math.radians(goal[0])
        prev_gvector = [self.goal[1]*math.cos(rad), self.goal[1]*math.sin(rad)] #old vector to goal 
        motion_vector = self.bat_pos
        new_gvector = [prev_gvector[0] - motion_vector[0], prev_gvector[1] - motion_vector[1]]        
        #new goal vector to calculate updated goal 
        new_goal = [math.degrees(math.atan2(new_gvector[1], new_gvector[0])), math.sqrt(new_gvector[0]**2 + new_gvector[1]**2)]    
        self.goal = new_goal
        self.bat_tile = [limt, limt]
        self.bat_pos = [0,0]
        #Now that bat and goal is "reset" start filling up obstacle queue 
        abs_fov = self.fov/2.
        filled_tiles = [] #don't want to fill tiles more than once 
        for obst in list_obstacles:  
            degrees = obst[0]
            distance = obst[1]
            radians = math.radians(degrees)
            row_index = int((math.cos(radians)*distance)/self.dist_pq) + limt
            col_index = int((math.sin(radians)*distance)/self.dist_pq) + limt
            spil_prob = (1-meas_certainty)/8. #spillover probability
            if [row_index, col_index] not in filled_tiles:
                if distance > self.mindist and distance < self.maxdist:
                    if degrees > -abs_fov and degrees < abs_fov: #only input detection with the field of view 
                        for i in range(-1, 2): 
                            for j in range(-1, 2): 
                                if i == 0 and j == 0: 
                                    self.obst_queue[row_index, col_index] = meas_certainty 
                                    filled_tiles.append([row_index, col_index])
                                else: 
                                    try: 
                                        self.obst_queue[row_index + i, col_index + j] += spil_prob
                                        self.obst_queue[row_index + i, col_index + j] += spil_prob
                                    except IndexError: 
                                        pass 
        #check if goal is in range, if not, generate fake_goal 
        goal = self.goal 
        rad = math.radians(goal[0])
        goal_row = int((math.cos(rad)*goal[1])/self.dist_pq) + limt
        goal_col = int((math.sin(rad)*goal[1])/self.dist_pq) + limt
        if goal_row >= 0 and goal_row < num_queue and goal_col >= 0 and goal_col < num_queue:
            self.real_goal = True 
        else: 
            goal_row = int((math.cos(rad)*self.maxdist)/self.dist_pq) + limt
            goal_col = int((math.sin(rad)*self.maxdist)/self.dist_pq) + limt
            counter = 0
            while self.obst_queue[goal_row, goal_col] > self.threshold: 
                if counter%2 == 0:
                    goal_row = goal_row - (math.cos(rad)/abs(math.cos(rad)))
                else: 
                    goal_col = goal_col - (math.cos(rad)/abs(math.cos(rad)))
                counter += 1
                
        self.goal_index = [goal_row, goal_col]
#        print self.goal_index
    
    def generate_waypts(self): 
        """
        generate wavepoints that avoids obstacles and reach goal, if no path can be found, 
        return None
        goal is given as the coordinate in cave (so basically, cave-frame)
        first, generate waypts, assuming that all value that has 
        not been detected is unoccupied. Then transform from polar from bat 
        point of view to rectangular and this must include goal. Transformation depends 
        on where the bat is facing. 
        an example of the new rectangular map looks like: 
        [1, 1, 1, 1, *]
        [0, 0, 0, #, 0]
        [0, 0, #, 1, 1]
        [0, #, 0, 1, 1]
        [1, B, 0, 0, 1] where B is the bat and * is the goal. Generate waypts (#) for optimal path from 
        bat to goal. 
        note that goal is given in polar coordinates as the angle and distance 
        So of course the goal value has to be updated every time one moves/change orientation 
        """
        start = self.bat_tile
        end = self.goal_index
        path = find_opt_path_As(self.obst_queue, start, end, self.threshold)
        self.path = path
    
    def smooth_path(self, weight_smooth=0.1, weight_data=0.1, tolerance=0.00001): 
        """
        taking self.path, the path generated by generate_waypts, smooth it as to allow smooth 
        navigation. Later apply PID controller. Assume the only absolutely fixed pts are the 
        starting pt and the end pt 
        """ 
        path = self.path[:]
        N = len(path)
        spath = copy.deepcopy(path)
        complete = False
        prev_change = 0
        while not complete:
            change = 0
            for i in range(1, N-1): 
                for j in range(2):
                    delta_d = weight_data*(path[i][j] - spath[i][j])
                    spath[i][j] += delta_d
                    delta_s = weight_data*(path[i-1][j] + spath[i+1][j] - 2.0*spath[i][j])
                    spath[i][j] += delta_s
                    change += (abs(delta_d) + abs(delta_s))
            if abs(change - prev_change) < tolerance:
                complete = True
            prev_change = change
        self.path = spath
    
    def motion_update(self, distance, direction, motion_certainty=0.8): 
        """
        update the obstacle queue with motion using simple vectors
        Note the Bayesian Inference: 
        P(L=l|X=x, Z=z) = P(Z=z|X=x, L=l)*P(X=x|L=l)*P(L=l)
        where L is landmark position, X is bat position, and Z is measurement 
        motion update is just the P(X=x|L=l)*P(L=l)
        Note that P(L=l) is just the prior probability 
        """
        grid = pylab.matrix(self.obst_queue)
        grid_shape = grid.shape
        rad = math.radians(direction)
        bat_delta_x = math.cos(rad)*distance
        bat_delta_y = math.sin(rad)*distance
        self.bat_pos[0] += bat_delta_x
        self.bat_pos[1] += bat_delta_y
        self.bat_tile[0] = int(self.bat_pos[0]/self.dist_pq) + (self.num_queue - 1)/2
        self.bat_tile[1] = int(self.bat_pos[1]/self.dist_pq) + (self.num_queue - 1)/2
        num_row = grid_shape[0]
        num_col = grid_shape[1]
        spilldex = [[1,0],[1,1],[0,1],[-1,1]] #which direction the "spill" is
        dex = int((direction - 22.5)/45)%4 #kind of crude way to do motion uncertainty 
        spill_dir = spilldex[dex]
        spill_prob = (1-motion_certainty)/2.
        filled_tiles = []
        for row in range(num_row): 
            for col in range(num_col):
                if [row, col] not in filled_tiles:
                    val = self.obst_queue[row, col]
                    grid[row, col] = val*motion_certainty
                    filled_tiles.append([row, col])
                    for i in range(1):
                        try: 
                            grid[row + spill_dir[0]*(-1)**i, col + spill_dir[1]*(-1)**i] += spill_prob*val 
                        except IndexError: #avoid out of range problems 
                            pass
                    
        return grid
    
    def meas_update(self, measurements, meas_certainty=0.9):
        """
        second part of Bayesian inference: measurement update
        P(Z=z|X=x, L=l)*P(X=x|L=l)*P(L=l) 
        Meas_certainty is the P(Z=z|X=x, L=l) part
        measurements is the new list of [[angle, dist],...] from the bat
        """ 
        new_grid = pylab.matrix(self.obst_queue)
        meas_index = [] #convert the measurements into index form for the matrix 
        spill_prob = (1-meas_certainty)/8. #spillover probability (the uncertainty)
        for meas in measurements:
            degrees = meas[0]
            distance = meas[1] 
            radians = math.radians(degrees)
            row_index = int((math.cos(radians)*distance)/self.dist_pq) + self.bat_tile[0]
            col_index = int((math.sin(radians)*distance)/self.dist_pq) + self.bat_tile[1]
            if [row_index, col_index] not in meas_index: #dont' have more than one 
                if row_index >= 0 and row_index < self.num_queue and col_index >=0 and col_index < self.num_queue:
                    meas_index.append([row_index, col_index])

        for tile in meas_index:
            for i in range(-1,2):
                for j in range(-1,2): 
                    a = tile[0] + i
                    b = tile[1] + j
                    if i == 0 and j == 0: 
                        new_grid[a,b] = self.obst_queue[a,b]*meas_certainty
                    else: 
                        if [a,b] not in meas_index: 
                            try: 
                                new_grid[a,b] = self.obst_queue[a,b]*spill_prob
                            except IndexError: 
                                pass
                            #need to check because dont want to multiply a detected 
                            #tile by a small probability 
        return new_grid 
        
    
    def check_pathclear(self):
        """
        check if after new motion update and detection update if original planned 
        path is still clear in order to determine whether to plan a new path 
        """
        grid = self.obst_queue
        path = self.path
        clear = True
        for step in path:
            if grid[int(step[0]), int(step[1])] > self.threshold:
                clear = False
                break
        return clear 
    
    def update_path(self, delta_dist, delta_ang):
        """
        path update for when the drone moves 
        """
        orig_path = self.path 
        new_path = []
        for step in orig_path:
            old_dist = step[0]*self.dist_pq + self.mindist 
            old_ang = (step[1]*self.deg_pq - 180.0)
            #apply delta_ang 
            ang1 = old_ang - delta_ang
            rad = math.radians(ang1)
            newx = (old_dist + self.dist_pq/2.)*(math.cos(rad))
            newy = (old_dist + self.dist_pq/2.)*(math.sin(rad)) - delta_dist
            new_ang = round(math.degrees(math.atan2(newy, newx)), 5)
            new_dist = math.sqrt(newx**2 + newy**2)
            if new_ang == 180:
                new_ang = 179 
            ang_index = (new_ang + 180.)/self.deg_pq
            dist_index = (new_dist - self.mindist)/self.dist_pq
            new_path.append([dist_index, ang_index])
        self.path = new_path

    def bat_nav_sim(self):
        """
        Navigate the bat around obstacles
        """
        limt = (self.num_queue - 1)/2
        #First step: initialize
        testcave = pb.cave(8,8,10)
        testbat = pb.bat(testcave, 90, 4, 0.1)
        self.maxdist = testbat.range
        self.fov = testbat.fov
        init_observ = testbat.sense_obstacle()
        self.initialize_queue(init_observ)
        goal_reached = False
        self.generate_waypts()
        #search for a new endpoint if the initial one doesn't work 
        count = 0
        #if can't find a path, shift the temporary goal around until 
        #a path can be found 
        while self.path == [] or self.path == None:
            go_ind = self.goal_index
            if go_ind[0] == 0 and go_ind[1] == 0:
                print "No Path Found"
                return False
            go_ind[count%2] -= 1
            self.goal_index = go_ind
            self.generate_waypts()
        self.smooth_path() #smooth the generated waypts 
        #initialize graphics
        actualobs = np.zeros((testcave.width, testcave.height))
        #matrix of obstacles for the visual 
        for obstacle in testcave.obstacles: 
            actualobs[obstacle[0], obstacle[1]] = 1
        visual = bv.bat_visualization(500) #initiate visual 
        seg_num = 1 #the pointer to the index of the path that the bat is currently on 
        current_origin = [testbat.get_bat_pos().get_x(), testbat.get_bat_pos().get_x()]
        #current origin maps what's going on in the bat sensing frame to whats going on in the 
        #cave, mostly for simulation purposes 
        while not goal_reached:
            print seg_num
            end = self.path[seg_num]
            if end == self.goal_index and self.real_goal:
                goal_reached = True
            end_bat_frame = [(end[0]-limt)*self.dist_pq + current_origin[0], (end[1]-limt)*self.dist_pq + current_origin[1]]           

            mvt_vector = [end_bat_frame[0] - self.bat_pos[0] - current_origin[0], end_bat_frame[1] - self.bat_pos[1] - current_origin[1]]
            dist = math.sqrt(mvt_vector[0]**2 + mvt_vector[1]**2)
            direc = math.degrees(math.atan2(mvt_vector[1], mvt_vector[0]))
            testbat.bat_line_follow(end_bat_frame, 120,800,30,visual,actualobs)
            self.motion_update(dist, direc)
            newmeas = testbat.sense_obstacle()
            self.meas_update(newmeas)
            condition = False #the if statement below accounts for the case of nearing goal 
            if not self.real_goal:
                if seg_num >= (len(self.path)-2):
                    condition = True 
            if not self.check_pathclear() or condition: #dictating when to reintialize obstacle detection grid
                #reinitializes when path isn't clear or if nearing the end of the generated path                 
                current_origin[0] += self.bat_pos[0] #move the mapping origin 
                current_origin[1] += self.bat_pos[1]
                self.initialize_queue(newmeas) #use new measurement to reinitilize new obst grid 
                self.generate_waypts() #again try to generate waypoints + smooth 
                while self.path == [] or self.path == None:
                    go_ind = self.goal_index
                    if go_ind[0] == 0 and go_ind[1] == 0:
                        print "No Path Found"
                        return False
                    go_ind[count%2] -= 1
                    self.goal_index = go_ind
                    self.generate_waypts()
                self.smooth_path()
                print "reinit"
                seg_num = 0  
#            if self.real_goal:
#                goal_reached = True 
            seg_num += 1
        print "arrived"
        visual.done()
            
           
test1 = Pushbroom(0, 4, 90, 0.5, [30., 8])
test1.bat_nav_sim()
#cave1 = pb.cave(8,8,20)
#bat1 = pb.bat(cave1, 90, 4)    
#sob = bat1.sense_obstacle()
#
#test = Pushbroom(0,3,90,0.5,[45., 4])
#test.initialize_queue(sob)
#print test.obst_queue
#print cave1.obstacles
##
#test.generate_waypts()
#test.smooth_path()
#print test.path
#visual = bv.bat_visualization(500)
#actualobs = np.zeros((cave1.width, cave1.height))
#actualobs = pylab.matrix(actualobs)
#for obstacle in cave1.obstacles: 
#    actualobs[obstacle[0], obstacle[1]] = 1
#visual.update(actualobs, bat1.position, 5, bat1.radius, bat1.direction, 90, 3)
#visual.done()
#
#pp = test1.path
#x = []
#y = []
#for step in pp: 
#    x.append(step[0])
#    y.append(step[1])
#pylab.plot(y,x)
#print test.check_pathclear()
#
##bat1.move(0,1)
##sob = bat1.sense_obstacle()
##print test.motion_update(0.2,0)
##print test.meas_update(sob)
##test.smooth_path()
##print test.path
##test.update_path(1,5)
##print test.path