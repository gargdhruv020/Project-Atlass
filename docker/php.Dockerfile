FROM php:7.4-apache

# Install mysqli and pdo_mysql for MySQL connectivity
RUN docker-php-ext-install mysqli pdo pdo_mysql

# Enable Apache mod_rewrite for CodeIgniter URL routing
RUN a2enmod rewrite

# Copy php portal files to Apache web root
COPY php-portal /var/www/html/

# Permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
