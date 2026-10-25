# Send update & restart signal to cPanel Phusion Passenger
Write-Host "Updating and restarting live application on cPanel..." -ForegroundColor Cyan

$remoteCmd = "cd /home/webkoders/indimusic.tv && /home/webkoders/virtualenv/indimusic.tv/3.11/bin/python manage.py migrate --noinput && /home/webkoders/virtualenv/indimusic.tv/3.11/bin/python manage.py collectstatic --noinput && mkdir -p tmp && touch tmp/restart.txt"

ssh -i "C:/Users/shuvo/.ssh/id_rsa" webkoders@195.250.26.201 $remoteCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "Application updated & restarted successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to update. Please check connection." -ForegroundColor Red
}
