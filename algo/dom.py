current_vid = 0


def mount(to, who):
    global current_vid
    current_vid = current_vid + 1
    who.vid = current_vid
    print(current_vid)
