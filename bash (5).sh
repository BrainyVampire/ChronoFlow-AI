# Используйте скрипт развертывания
./scripts/deploy.sh

# Настройте SSL сертификаты
certbot --nginx -d yourdomain.com

# Настройте резервное копирование
crontab -e
# Добавьте: 0 2 * * * /app/scripts/backup_db.sh