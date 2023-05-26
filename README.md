# Practice Chat overview

[Practice Chat](https://practicechat.com) is a team collaboration tool that combines the best of email and chat to
make remote work productive and delightful.

Come find us on the [developer team website](https://axe.software/about-us/)!

## Practice Chat Deployment to Production

### Step 1 : Create ```zulip``` user

```sudo adduser zulip```\
```sudo usermod -aG sudo zulip```\
#### **You can set the password  whatever you want for the user ```zulip```.**

### Step 2 : Download the latest source code

- Check out our [source code](https://github.com/Axe-LLC/zulip)
  to get started.
- Run ```su - zulip``` to switch to ```zulip``` user.
- Run ```git clone git@github.com:Axe-LLC/zulip.git``` to clone the repository
- Run ```cd zulip``` to go to the source directory

### Step 3 : Installation

- **Domain Purchase and Configuration**.\
-Make sure that you already purchased the domain (```practicechat.app```)\
-Add a CNAME record to your domain's DNS records


- **Install Practice Chat**.\
```./scripts/setup/install --certbot --email=ADMINISTRATOR_EMAIL --hostname=practicechat.app```\
This takes a few minutes to run as it install all the packages and dependencies.
  <details>
  <summary>The install script does several things</summary>

  - Creates /home/zulip/deployments/, which the Zulip code for this deployment (and future deployments when you upgrade) goes into. At the very end of the install process, the script moves the Zulip code tree it’s running from (which you unpacked from a tarball above) to a directory there, and makes /home/zulip/deployments/current as a symbolic link to it.
  - Installs Zulip’s various dependencies.
  - Configures the various third-party services Zulip uses, including PostgreSQL, RabbitMQ, Memcached and Redis.
  - Initializes Zulip’s database.
  </details>
  <details>
  <summary>Installer Options</summary>

  - ```--email=you@example.com```: The email address for the person or team who maintains the Practice Chat installation. Note that this is a public-facing email address; it may appear on 404 pages, is used as the sender’s address for many automated emails, and is advertised as a support address
  - ```--hostname=zulip.example.com```: The user-accessible domain name for this Practice Chat server, i.e., what users will type in their web browser. This becomes ```EXTERNAL_HOST``` in the Practice Chat settings.
  - Configures the various third-party services Practice Chat uses, including PostgreSQL, RabbitMQ, Memcached and Redis.
  - Initializes Practice Chat’s database.
  </details>


- **Configure the Nginx server**.\
```sudo cp /home/zulip/deployments/current/nginx.conf /etc/nginx/sites-available/zulip```\
```sudo ln -s /etc/nginx/sites-available/zulip /etc/nginx/sites-enabled/zulip```\
```sudo systemctl restart nginx```
  <details>
  <summary>/etc/nginx/sites-available/zulip.conf</summary>

      server {
          server_name practicechat.app www.practicechat.app;
          listen 80;
          listen [::]:80;

          location / {
              return 301 https://$host$request_uri;
          }

          include /etc/nginx/zulip-include/certbot;
      }

      include /etc/nginx/zulip-include/s3-cache;
      include /etc/nginx/zulip-include/upstreams;
      include /etc/zulip/nginx_sharding_map.conf;


      server {
          server_name practicechat.app www.practicechat.app;
          listen 443 ssl http2;
          listen [::]:443 ssl http2;

          ssl_certificate /etc/ssl/certs/zulip.combined-chain.crt;
          ssl_certificate_key /etc/ssl/private/zulip.key;

          location /local-static {
              alias /home/zulip/local-static;
          }

          include /etc/nginx/zulip-include/certbot;
          include /etc/nginx/zulip-include/app;
      }

  </details>


- **Obtain SSL certificate for your domain**.\
```sudo certbot --nginx -d practicechat.app www.practicechat.app```


- **Email Gateway Configuration**. <br/>
```/etc/zulip/settings.py```\
You can set **EMAIL_HOST**, **EMAIL_HOST_USER**, **EMAIL_USE_TLS**, **EMAIL_USE_TLS**, **DEFAULT_FROM_EMAIL**, **EXTERNAL_HOST** in this file.\
It must be different per email service provider (Sendgrid, Mailgun, Mailchimp).<br/><br/>
```/etc/zulip/zulip-secrets.conf```\
Passwords and secrets are not stored in /etc/zulip/settings.py. The password goes in /etc/zulip/zulip-secrets.conf.\
In this file, set `email_password`. <br/><br/>
  <details>
  <summary>/etc/zulip/settings.py</summary>

      EMAIL_HOST = "smtp.mailgun.org"
      EMAIL_HOST_USER = "postmaster@axe.software"
      EMAIL_USE_TLS = True
      EMAIL_PORT = 587
      DEFAULT_FROM_EMAIL = "zach@axe.software"

  </details>


- **Restart the backend server**.\
You can restart the server whenever you make changes to the backend using this command ```./scripts/restart-server```<br/><br/>

- **Restart the frontend server (webpack bundling)**.\
You can rebuild the frontend whenever you make changes to the frontend (css, js, images) using this command ```./tools/update-prod-static```

### Step 4 : Multiple Organization

Coming soon
