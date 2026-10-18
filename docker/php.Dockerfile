FROM php:7.4-apache

# Install required PHP extensions for MySQL connectivity and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install mysqli pdo pdo_mysql

# Enable Apache mod_rewrite for CodeIgniter 3 routing
RUN a2enmod rewrite

# Allow .htaccess overrides in Apache webroot
RUN sed -i 's/AllowOverride None/AllowOverride All/g' /etc/apache2/apache2.conf

# Copy CodeIgniter 3 application to Apache webroot
COPY php-portal /var/www/html/

# Ensure web server ownership
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80

# Health check against PHP portal front controller
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=10s \
    CMD curl -f http://localhost/ || exit 1

CMD ["apache2-foreground"]
