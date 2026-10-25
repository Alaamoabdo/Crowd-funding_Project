# 🚀 Crowd-Funding Web Application

A full-stack crowdfunding platform designed and built for the Egyptian market, enabling users to create, discover, and fund innovative projects. 

---

## ✨ Key Features

### 1. 🔐 Robust Authentication & User Management
* **Secure Registration:** Collects First Name, Last Name, Email, Password, Profile Picture, and Mobile Phone (validated specifically for Egyptian phone formats).
* **Email Activation:** Sends an automated activation link upon registration (expires after 24 hours) to secure accounts against spam.
* **Controlled Access:** Users cannot log in until their account is successfully activated.
* **Comprehensive Profile Management:** 
  * View personal profile details, user-created projects, and donation history.
  * Edit profile information (excluding email) and add optional data (Birthdate, Facebook profile, Country).
  * Account deletion feature with a security confirmation prompt (requiring password verification).

### 2. 📁 Project Creation & Campaign Management
* **Campaign Details:** Title, detailed description, categories (managed by admins), and multiple target fundraising goals (e.g., in EGP).
* **Media & Customization:** Multiple image support with an interactive slider view, and multiple tags for effective categorization.
* **Lifecycle Controls:** Set custom start and end times for campaigns. Creators can cancel their project if total donations are below 25% of the target goal.

### 3. 💬 Community Engagement & Interaction
* **Donation System:** Secure flow allowing users to contribute funds towards project targets.
* **Interactive Comments:** Users can comment on projects (with nested replies support).
* **Moderation & Reporting:** Built-in reporting mechanism for inappropriate projects and comments.
* **Rating System:** Project rating functionality with dynamic overall average rating calculation displayed on the project page.
* **Recommendation Engine:** Smart discovery section displaying 4 similar projects based on matching project tags.

### 4. 🏠 Feature-Rich Homepage
* **Top Rated Slider:** Highlights the highest five rated running campaigns to drive user donations.
* **Latest & Featured Lists:** Dedicated sections showcasing the latest 5 projects and featured projects selected by administrators.
* **Category Navigation:** Interactive category list allowing users to filter and explore project listings.
* **Global Search:** Fast search bar enabling users to find projects instantly by title or tags.
