#influence counter

#given a twitter user, calculate their influence in the new system

def find_mutual_connections(username):
    if username == "dan":
        return {"user1","user2","user3"}
    elif username == "user1":
        return {"user4","user5","user6"}
    else:
        return set()

def influence(username):
    
    infl = 0

    frontier = {username,}
    connected = {username,}

    depth = 1

    finished
    while frontier != set():

        new_connections = set()
        for user in frontier:
            new_connections = new_connections | find_mutual_connections(user)

        frontier = new_connections.difference(connected)
        connected = connected|new_connections
        
        infl += len(frontier)*.5**depth
        depth += 1

    return infl

print(influence("dan"))
