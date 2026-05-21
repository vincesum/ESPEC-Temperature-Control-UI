'''Tasks.py: Defines the Task and LinkedList classes for managing oven tasks. List implements a queue using a linked list structure.
'''

import threading
#A single node in a linked list
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
        self.active = False
        self.finished = False
        return

class LinkedList:
    def __init__(self):
        self.head = None
        
        return

    def enqueue(self, data):
        new_node = Node(data)

        if not self.head:
            self.head = new_node
            return

        current = self.head
        while current.next:
            current = current.next

        current.next = new_node
        return

    def pop_head(self):
        if not self.head:
            raise IndexError("Pop from empty list")
        self.head = self.head.next
        return

    def print_list(self):
        current = self.head
        i = 1
        print("Task List:")
        while current:
            if current.data.taskName == "Task":
                print("Task "+ str(i) + ": " + "temp: " + str(current.data.temp) + "°C, " + "duration: " + current.data.hours + "hr " + current.data.minutes + "min " + current.data.seconds + "s")
            elif current.data.taskName == "Idle":
                print("Task "+ str(i) + ": " + "Idle for: " + current.data.hours + "hr " + current.data.minutes + "min " + current.data.seconds + "s")
            else:
                print("Task "+ str(i) + ": " + "Cycle from: " + str(current.data.temp1) + "°C, " + "to " + str(current.data.temp2) + "°C for duration: " + current.data.hours + "hr " + current.data.minutes + "min " + current.data.seconds + "s for " + str(current.data.totalCycles) + " cycles")
            i += 1
            current = current.next
        return


    
    


    #Defines the structure of a Task
class Task:
    def __init__(self, temp, hours, minutes, seconds, taskName="Task", db_id=None):
        self.temp = temp
        self.hours = str(hours)
        self.minutes = str(minutes)
        self.seconds = str(seconds)
        self.durationInSeconds = (hours * 3600 + minutes * 60 + seconds)
        self.taskName = taskName
        self.db_id = db_id
        return
