from Tasks import Task
class Cycle(Task):
    """
    Cycle class that subclasses Task
    Takes in temp1, temp2 and totalCycles as additional parameters that is used for the cycle task
    Cycles in between temp1 and temp2 for a total number of totalCycles
    """
    def __init__(self, temp1, temp2, hours, minutes, seconds, totalCycles, taskName, db_id):
        self.temp1 = temp1
        self.temp2 = temp2
        self.hours = str(hours)
        self.minutes = str(minutes)
        self.seconds = str(seconds)
        self.durationInSeconds = (hours * 3600 + minutes * 60 + seconds)
        self.totalCycles = totalCycles
        self.taskName = taskName
        self.db_id = db_id
        return
