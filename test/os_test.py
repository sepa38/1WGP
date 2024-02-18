import os


startDate = "2024-02-17_22-47-50"
currentTurn = 0
userIndex = 0
targetPath = os.path.join(startDate, str(currentTurn))
targetPath = os.path.join(targetPath, str(userIndex))

with open(os.path.join(targetPath, "subject.txt"), mode = "w") as f:
  f.write("a")