@echo off
echo Server.py Running:
set /p IP="Enter IP Address: "
set /p PORT="Enter Port: "
set /p PROTOCOL="Enter Protocol (tcp/udp): "

python server.py %IP% %PORT% %PROTOCOL%