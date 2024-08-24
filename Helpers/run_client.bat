@echo off
echo Client.py Running:
set /p IP="Enter IP Address: "
set /p PORT="Enter Port: "
set /p PROTOCOL="Enter Protocol (tcp/udp): "
set /p MESSAGE="Enter Message: "

python client.py %IP% %PORT% %PROTOCOL% %MESSAGE%