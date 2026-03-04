# Travel Booking System

A comprehensive web application for booking travel accommodations, viewing travel destinations, and managing hotel operations.

## Features

### User Features
- **User Authentication**: Secure login and registration system
- **Hotel Search & Booking**: Search for hotels and manage bookings
- **Explore Destinations**: Discover travel places with detailed information
- **My Bookings**: Track and manage personal hotel bookings
- **User Dashboard**: Personalized user dashboard

### Hotel Owner Features
- **Hotel Registration & Management**: Register and manage hotel properties
- **Room Management**: Add and manage hotel rooms
- **Booking Management**: View and manage guest bookings
- **Revenue Tracking**: Monitor hotel revenue and booking statistics
- **Hotel Images**: Upload and manage hotel images
- **Hotel Dashboard**: Dedicated hotel owner dashboard

### Guide Features
- **Guide Registration**: Register as a travel guide
- **Guide Dashboard**: Manage guide assignments and information
- **Guide Updates**: Submit and manage guide-related updates

### Admin Features
- **Admin Dashboard**: Comprehensive admin control panel
- **Hotel Approvals**: Approve or reject hotel registrations
- **Hotel Management**: Manage all hotels in the system
- **Booking Monitoring**: View all hotel bookings
- **Guide Management**: Manage travel guides and their assignments
- **User Analytics**: View system statistics and analytics

## Project Structure

```
travel_booking_system/
├── app.py                          # Main Flask application
├── templates/                      # HTML templates
│   ├── index.html                 # Home page
│   ├── login.html                 # User login
│   ├── signup.html                # User registration
│   ├── dashboard.html             # User dashboard
│   ├── hotel_login.html           # Hotel owner login
│   ├── hotel_register.html        # Hotel registration
│   ├── hotel_dashboard.html       # Hotel owner dashboard
│   ├── admin_login.html           # Admin login
│   ├── admin_dashboard.html       # Admin dashboard
│   ├── guide_login.html           # Guide login
│   ├── guide_dashboard.html       # Guide dashboard
│   └── [other hotel/booking/guide templates]
├── static/                         # Static files
│   ├── css/
│   │   └── modern.css             # Modern styling
│   ├── images/                    # Image resources
│   ├── hotel_images/              # Hotel images
│   ├── place_images/              # Place/destination images
│   ├── videos/                    # Video resources
│   └── uploads/                   # User uploaded files
└── README.md                       # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd travel_booking_system
   ```

2. **Create and activate a virtual environment**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`

## Usage

### For Users
1. Sign up or log in to your account
2. Browse hotels or destinations
3. Search for available hotels
4. Make a booking and complete payment
5. View your bookings in "My Bookings"

### For Hotel Owners
1. Register your hotel on the platform
2. Wait for admin approval
3. Log in to your hotel dashboard
4. Add rooms and manage inventory
5. Manage bookings and track revenue

### For Travel Guides
1. Register as a travel guide
2. Log in to guide dashboard
3. Receive guide assignments
4. Update guide information

### For Admins
1. Log in with admin credentials
2. Access the admin dashboard
3. Approve/manage hotel registrations
4. Monitor bookings and revenue
5. Manage guides and assignments

## Database

The application uses a database to store:
- User accounts and authentication
- Hotel information and availability
- Room details and pricing
- Booking records and transactions
- Guide information and assignments
- Admin management data

## Security Features

- Secure password hashing
- User authentication and authorization
- Admin-only restricted pages
- Input validation and sanitization
- Session management

## Technologies Used

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **Database**: [Database system - to be specified]
- **Authentication**: Flask session management
- **File Handling**: Image and video uploads

## Contributing

To contribute to this project:
1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## Support

For support or issues, please:
1. Check existing issues
2. Create a detailed bug report
3. Include steps to reproduce
4. Attach relevant screenshots

## Contact

For more information or inquiries, [contact information]

---

**Last Updated**: March 2026
