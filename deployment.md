# Complete AWS Free-Tier Deployment Guide

Deploying headless browsers like Chromium requires careful memory management. The absolute **simplest and 100% Free-Tier eligible** strategy on AWS is launching a single **EC2 (Elastic Compute Cloud)** virtual machine running Docker.

This avoids the costs of Load Balancers, ECS Clusters, and EFS network drives.

---

## 1. Launch the Free-Tier EC2 Instance

1. Log into your **AWS Management Console** and navigate to **EC2**.
2. Click **Launch Instances**.
3. **Name:** `linkedin-scraper-server`
4. **OS Level (AMI):** Select **Ubuntu 24.04 LTS** (Marked "Free tier eligible").
5. **Instance Type:** Select **t2.micro** or **t3.micro** (1 vCPU, 1 GB RAM - Free tier eligible).
6. **Key Pair:** Create a new RSA key pair (`scraper-key.pem`) and download it. You need this to connect!
7. **Network Settings (Security Group):**
   - Check **Allow SSH traffic** (Port 22).
   - Check **Allow HTTP traffic** (Port 80).
   - **Important:** Click 'Edit' on network settings, and add a **Custom TCP Rule** for **Port 5000** with source `0.0.0.0/0` (Anywhere). This allows the internet to reach your scraper API.
8. **Storage:** Set to **20 GB** `gp3` (up to 30GB is completely free). Chromium and Docker need space.
9. Click **Launch Instance**.

---

## 2. Connect and Prepare the Server

Headless browsers crash instantly if a server runs out of RAM. A `t2.micro` only has 1 GB of RAM, which is cutting it incredibly close.
**We will fix this by creating 2GB of "Swap Space" (Fake RAM on the hard drive).**

1. Connect to your instance via SSH using your terminal (if using powershell/cmd or terminal on Mac/Linux):

   ```bash
   ssh -i "scraper-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
   ```

2. Run the following commands exactly as written to create the 2GB Swap Space:
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

---

## 3. Install Docker on the EC2

Run these commands to install Docker natively:

```bash
# Update server
sudo apt-get update -y

# Install Docker
sudo apt-get install docker.io -y

# Allow your user to run Docker without typing "sudo" every time
sudo usermod -aG docker ubuntu
```

_(You must type `exit` to disconnect from the server, then SSH back in for the Docker permissions to apply)._

---

## 4. Deploy the Application!

Now that the server is bulletproof, pull your code and run the scraper.

1. **Upload your code** to the EC2. (You can `git clone` your repository from GitHub once uploaded, or use a tool like WinSCP/FileZilla to copy your folder).

   ```bash
   git clone <YOUR_GITHUB_REPO_URL>
   cd linkedin-web
   ```

2. **Create your `.env` file** on the server:

   ```bash
   cp .env.example .env
   # You can edit it using: nano .env
   ```

3. **Build the Optimized Docker Container:**

   ```bash
   docker build -t scraper-app:latest .
   ```

   _(This will take about 3-5 minutes depending on the AWS network)._

4. **Run the Server in the Background:**
   ```bash
   sudo docker run -d \
     --name linkedin-api \
     --restart unless-stopped \
     -p 5000:5000 \
     --env-file .env \
     scraper-app:latest
   ```

---

## 5. Verify and Use

Your production server is fundamentally online forever!

- **Test the API:** Open your web browser and go to: `http://<YOUR_EC2_PUBLIC_IP>:5000`
- **Restarting?** Because of the `--restart unless-stopped` flag in our Docker command, if AWS reboots your server for underlying maintenance, Docker will automatically start your scraper API back up the second the server turns on. No manual startup required.
- **View Live Logs:** If you ever want to see what Chromium is doing inside the server, simply SSH into the machine and run: `docker logs -f linkedin-api`
