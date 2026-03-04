from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.utils import secure_filename
from datetime import date, datetime
import os
import mysql.connector
import re
from flask import request, redirect, render_template, session, flash

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Nisha@04",
    database="travel_booking"
)
cursor = db.cursor(dictionary=True)

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered!", "warning")
            return redirect('/signup')

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (fullname, email, password)
        )
        db.commit()
        flash("Account created successfully! Please login.", "success")
        return redirect('/login')

    return render_template('signup.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome, {user['name']}!", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid email or password!", "danger")

    return render_template('login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/login')

    return render_template(
        'dashboard.html',
        username=session.get('user_name')
    )

# ---------------- HELP/SUPPORT ----------------
@app.route('/help')
def help():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/login')
    
    return render_template('help.html', username=session.get('user_name'))

@app.route('/explore', methods=['GET', 'POST'])
def explore():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/login')

    if request.method == 'POST':
        days = request.form.get('days')
        region = request.form.get('region')

        if days == '1-2':
            min_d, max_d = 1, 2
        elif days == '3-4':
            min_d, max_d = 3, 4
        elif days == '5-7':
            min_d, max_d = 5, 7
        else:
            min_d, max_d = 8, 30

        if region == 'Anywhere in India':
            cursor.execute(
                "SELECT * FROM places WHERE min_days <= %s AND max_days >= %s",
                (max_d, min_d)
            )
        else:
            cursor.execute(
                """SELECT * FROM places
                   WHERE region=%s AND min_days <= %s AND max_days >= %s""",
                (region, max_d, min_d)
            )
    else:
        cursor.execute("SELECT * FROM places")

    places = cursor.fetchall()

    places_data = []
    for place in places:
        cursor.execute(
            "SELECT image_name FROM place_images WHERE place_id=%s",
            (place['id'],)
        )
        images = [img['image_name'] for img in cursor.fetchall()]

        places_data.append({
            'id': place['id'],
            'place_name': place['place_name'],
            'min_days': place['min_days'],
            'max_days': place['max_days'],
            'images': images
        })

    return render_template(
        'explore.html',
        username=session.get('user_name'),
        places=places_data
    )

# ---------------- BOOKING ----------------
@app.route('/book/<int:place_id>', methods=['GET', 'POST'])
def book(place_id):
    cursor = db.cursor(dictionary=True)

    # Fetch the place
    cursor.execute("SELECT * FROM places WHERE id=%s", (place_id,))
    place = cursor.fetchone()

    # Fetch the spots for this place
    cursor.execute(
        "SELECT spot_name, extra_price FROM place_spots WHERE place_id=%s",
        (place_id,)
    )
    spots = cursor.fetchall()

    # Determine selected spot (default first spot if not selected yet)
    selected_spot = request.args.get('spot')  # from query param
    if not selected_spot and spots:
        selected_spot = spots[0]['spot_name']

    # Fetch hotels only in the selected spot
    cursor.execute("""
        SELECT h.*, GROUP_CONCAT(i.image_name) AS images
        FROM hotels h
        LEFT JOIN hotel_images i ON h.id=i.hotel_id
        WHERE h.place_id=%s AND h.spot_name=%s AND h.status='Approved'
        GROUP BY h.id
    """, (place_id, selected_spot))
    hotels_raw = cursor.fetchall()

    # Prepare hotels for template
    hotels = []
    for h in hotels_raw:
        hotels.append({
            'id': h['id'],
            'hotel_name': h['hotel_name'],
            'address': h['address'],
            'price_per_night': h['price_per_night'],
            'available_rooms': h['available_rooms'],
            'images': h['images'] if h['images'] else '',
            'spot_name': h['spot_name']
        })

    return render_template(
        "booking.html",
        place=place,
        spots=spots,
        selected_spot=selected_spot,
        hotels=hotels
    )


# ---------- PAYMENT ----------
@app.route('/payment', methods=['POST'])
def payment():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/login')

    cursor = db.cursor(dictionary=True)
    data = request.form

    # Validate payment method
    payment_method = data.get('payment_method')
    if not payment_method:
        flash("Please select a payment method.", "warning")
        return redirect(request.referrer)

    # Final price (calculated in frontend)
    final_price = float(data['total_price'])

    # Admin selected spots (comma separated string)
    admin_spots = data.get('admin_spots')

    # User suggested spots (textarea)
    user_suggestions = data.get('user_suggestions')

    # Combine both into ONE column
    all_spots = []

    if admin_spots:
        all_spots.extend([s.strip() for s in admin_spots.split(',') if s.strip()])

    if user_suggestions:
        all_spots.extend([s.strip() for s in user_suggestions.split(',') if s.strip()])

    suggested_places = ",".join(all_spots) if all_spots else None

    # Insert booking
    cursor.execute("""
        INSERT INTO bookings
        (user_id, booking_name, place_id, days, persons, price,
         travel_date, pickup_location, suggested_places,
         payment_method, email, phone)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        session['user_id'],
        data['name'],
        data['place_id'],
        data['days'],
        data['persons'],
        final_price,
        data['travel_date'],
        data['pickup_location'],
        suggested_places,
        payment_method,  # only 'cash' or whatever the user selects
        data['email'],
        data['phone']
    ))

    db.commit()
    flash("Booking confirmed! You will be contacted by the tour guide for payment.", "success")
    return redirect(url_for('booking_success'))

# ---------- SUCCESS ----------
@app.route('/booking_success')
def booking_success():
    return render_template("booking_success.html")

@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect('/login')

    cursor.execute("""
        SELECT 
            b.*,
            p.place_name,
            tg.guide_name,
            tg.phone AS guide_phone,
            tg.email AS guide_email
        FROM bookings b
        JOIN places p ON b.place_id = p.id
        LEFT JOIN tourist_guides tg ON b.guide_id = tg.id
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """, (session['user_id'],))

    bookings = cursor.fetchall()
    return render_template('my_bookings.html', bookings=bookings)


# ---------------- ADMIN LOGIN ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        admin = cursor.fetchone()

        if admin:
            # Set admin session variables
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['username']
            flash("Admin login successful!", "success")
            return redirect('/admin_dashboard')  # <-- redirect to admin dashboard
        else:
            flash("Invalid admin credentials!", "danger")

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')
    return render_template('admin_dashboard.html')

@app.route('/add_place', methods=['GET', 'POST'])
def add_place():
    if 'admin_id' not in session:
        return redirect('/admin')

    if request.method == 'POST':
        place_name = request.form['place_name']
        region = request.form['region']
        min_days = request.form['min_days']
        max_days = request.form['max_days']

        # ✅ CORRECT FIELD NAMES
        spot_names = request.form.getlist('spot_name[]')
        extra_prices = request.form.getlist('extra_price[]')

        images = request.files.getlist('images[]')

        # 1️⃣ Insert place
        cursor.execute(
            "INSERT INTO places (place_name, region, min_days, max_days) VALUES (%s,%s,%s,%s)",
            (place_name, region, min_days, max_days)
        )
        place_id = cursor.lastrowid

        # 2️⃣ Insert visiting spots WITH PRICE
        for name, price in zip(spot_names, extra_prices):
            cursor.execute(
                "INSERT INTO place_spots (place_id, spot_name, extra_price) VALUES (%s,%s,%s)",
                (place_id, name, price)
            )

        # 3️⃣ Save images
        upload_folder = 'static/place_images'
        os.makedirs(upload_folder, exist_ok=True)

        for image in images:
            if image and image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(upload_folder, filename))

                cursor.execute(
                    "INSERT INTO place_images (place_id, image_name) VALUES (%s,%s)",
                    (place_id, filename)
                )

        db.commit()
        flash("Place, spots and images added successfully", "success")
        return redirect('/admin_dashboard')

    return render_template('add_place.html')


@app.route('/manage_bookings')
def manage_bookings():
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            b.id,
            b.booking_name,
            b.email,
            b.phone,
            b.persons,
            b.days,
            b.travel_date,
            b.pickup_location,
            b.suggested_places,
            b.price,
            b.booking_date,
            b.payment_method,
            b.status,
            b.guide_id,
            p.place_name,
            g.guide_name
        FROM bookings b
        JOIN places p ON b.place_id = p.id
        LEFT JOIN tourist_guides g ON b.guide_id = g.id
        ORDER BY b.booking_date DESC
    """)

    bookings = cursor.fetchall()
    return render_template('manage_bookings.html', bookings=bookings)


@app.route('/update_booking_status/<int:booking_id>/<status>')
def update_booking_status(booking_id, status):
    if 'admin_id' not in session:
        flash("Admin login required!", "danger")
        return redirect('/admin')

    if status not in ['Approved', 'Rejected']:
        flash("Invalid status!", "danger")
        return redirect('/manage_bookings')

    cursor.execute("""
        UPDATE bookings
        SET status = %s
        WHERE id = %s
    """, (status, booking_id))
    db.commit()

    flash(f"Booking {status} successfully!", "success")
    return redirect('/manage_bookings')

@app.route('/delete_booking/<int:id>')
def delete_booking(id):
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    cursor.execute("DELETE FROM bookings WHERE id=%s", (id,))
    db.commit()
    flash("Booking deleted successfully!", "success")
    return redirect('/manage_bookings')

@app.route('/assign_guide/<int:booking_id>', methods=['GET', 'POST'])
def assign_guide(booking_id):
    if 'admin_id' not in session:
        return redirect('/admin')

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        guide_id = request.form['guide_id']

        # Assign guide to booking
        cursor.execute("""
            UPDATE bookings 
            SET guide_id=%s, status='Approved'
            WHERE id=%s
        """, (guide_id, booking_id))

        # Make guide unavailable
        cursor.execute("""
            UPDATE tourist_guides
            SET is_available=0
            WHERE id=%s
        """, (guide_id,))

        db.commit()
        flash("Guide assigned successfully!", "success")
        return redirect('/manage_bookings')

    # Get booking
    cursor.execute("SELECT * FROM bookings WHERE id=%s", (booking_id,))
    booking = cursor.fetchone()

    # Get only available guides
    cursor.execute("SELECT * FROM tourist_guides WHERE is_available=1")
    guides = cursor.fetchall()

    return render_template(
        'assign_guide.html',
        booking=booking,
        guides=guides
    )



@app.route('/view_places')
def view_places():
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    cursor.execute("SELECT * FROM places")
    places = cursor.fetchall()
    return render_template('view_places.html', places=places)

# Edit Place
@app.route('/edit_place/<int:id>', methods=['GET', 'POST'])
def edit_place(id):
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    if request.method == 'POST':
        place_name = request.form['place_name']
        region = request.form['region']
        min_days = request.form['min_days']
        max_days = request.form['max_days']
        description = request.form['description']

        cursor.execute(
            "UPDATE places SET place_name=%s, region=%s, min_days=%s, max_days=%s, description=%s WHERE id=%s",
            (place_name, region, min_days, max_days, description, id)
        )
        db.commit()
        flash("Place updated successfully!", "success")
        return redirect('/view_places')

    cursor.execute("SELECT * FROM places WHERE id=%s", (id,))
    place = cursor.fetchone()
    return render_template('edit_place.html', place=place)

# Delete Place
@app.route('/delete_place/<int:id>')
def delete_place(id):
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    cursor.execute("DELETE FROM places WHERE id=%s", (id,))
    db.commit()
    flash("Place deleted successfully!", "success")
    return redirect('/view_places')

@app.route('/add_guide', methods=['GET', 'POST'])
def add_guide():
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    if request.method == 'POST':
        name = request.form['guide_name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        places = request.form.getlist('places[]')

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO tourist_guides (guide_name, phone, email, password, is_available) VALUES (%s,%s,%s,%s,1)",
            (name, phone, email, password)
        )
        db.commit()
        guide_id = cursor.lastrowid

        for place in places:
            cursor.execute(
                "INSERT INTO guide_places (guide_id, place_name) VALUES (%s,%s)",
                (guide_id, place)
            )
        db.commit()
        flash("Tourist guide added successfully!", "success")
        return redirect('/add_guide')  # redirect to refresh list

    # Fetch all guides with places
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tourist_guides")
    guides = cursor.fetchall()

    # Attach places to each guide
    for guide in guides:
        cursor.execute("SELECT * FROM guide_places WHERE guide_id=%s", (guide['id'],))
        guide['places'] = cursor.fetchall()

    return render_template('add_guide.html', guides=guides)

@app.route('/guide_login', methods=['GET', 'POST'])
def guide_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM tourist_guides WHERE email=%s AND password=%s",
            (email, password)
        )
        guide = cursor.fetchone()

        if guide:
            session['guide_id'] = guide['id']
            session['guide_name'] = guide['guide_name']
            flash(f"Welcome {guide['guide_name']}!", "success")
            return redirect('/guide_dashboard')
        else:
            flash("Invalid username or password", "danger")

    return render_template('guide_login.html')

@app.route('/guide_dashboard')
def guide_dashboard():
    if 'guide_id' not in session:
        return redirect('/guide_login')

    # Fetch all bookings assigned to this guide
    cursor.execute("""
        SELECT 
            b.id,
            b.booking_name,
            b.phone,
            b.email,
            b.travel_date,
            b.pickup_location,
            b.assigned_place,
            b.days,
            b.persons,
            b.status,
            b.suggested_places
        FROM bookings b
        WHERE b.guide_id = %s
        ORDER BY b.travel_date
    """, (session['guide_id'],))

    assignments = cursor.fetchall()

    # Fetch guide updates for each booking
    for a in assignments:
        cursor.execute("""
            SELECT location, message, created_at
            FROM guide_updates
            WHERE booking_id=%s
            ORDER BY created_at
        """, (a['id'],))
        a['updates'] = cursor.fetchall()

    return render_template(
        'guide_dashboard.html',
        guide_name=session['guide_name'],
        assignments=assignments
    )


@app.route('/complete_trip/<int:booking_id>', methods=['POST'])
def complete_trip(booking_id):
    if 'guide_id' not in session:
        return redirect('/guide_login')

    # Verify booking belongs to this guide
    cursor.execute("""
        SELECT guide_id FROM bookings WHERE id=%s
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking or booking['guide_id'] != session['guide_id']:
        flash("Unauthorized action!", "danger")
        return redirect('/guide_dashboard')

    # Mark booking completed
    cursor.execute("""
        UPDATE bookings
        SET status='Completed'
        WHERE id=%s
    """, (booking_id,))

    # Make guide available again
    cursor.execute("""
        UPDATE tourist_guides
        SET is_available=1
        WHERE id=%s
    """, (session['guide_id'],))

    db.commit()
    flash("Trip marked as completed!", "success")
    return redirect('/guide_dashboard')

@app.route('/update_progress/<int:booking_id>', methods=['POST'])
def update_progress(booking_id):
    if 'guide_id' not in session:
        return redirect('/guide_login')

    location = request.form.get('location')
    message = request.form.get('message', '')

    cursor.execute("""
        INSERT INTO guide_updates (booking_id, guide_id, location, message)
        VALUES (%s, %s, %s, %s)
    """, (booking_id, session['guide_id'], location, message))
    db.commit()

    flash("Progress updated!", "success")
    return redirect('/guide_dashboard')

@app.route('/admin_guide_updates')
def admin_guide_updates():
    if 'admin_id' not in session:
        flash("Please login as admin!", "warning")
        return redirect('/admin')

    cursor.execute("""
        SELECT 
            gu.id,
            gu.location,
            gu.message,
            gu.created_at,
            tg.guide_name,
            b.id AS booking_id,
            p.place_name,
            b.booking_name
        FROM guide_updates gu
        JOIN tourist_guides tg ON gu.guide_id = tg.id
        JOIN bookings b ON gu.booking_id = b.id
        JOIN places p ON b.place_id = p.id
        ORDER BY gu.created_at DESC
    """)

    updates = cursor.fetchall()

    return render_template(
        'admin_guide_updates.html',
        updates=updates
    )

@app.route("/hotel_register", methods=["GET","POST"])
def hotel_register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        # Check if email already exists
        cursor.execute(
            "SELECT * FROM hotel_owners WHERE email=%s",
            (email,)
        )
        existing = cursor.fetchone()

        if existing:
            flash("Email already registered!", "danger")
            return redirect("/hotel_register")

        # Insert new owner (USE owner_name)
        cursor.execute(
            "INSERT INTO hotel_owners (owner_name, email, password, hotel_id) VALUES (%s,%s,%s,NULL)",
            (name, email, password)
        )
        db.commit()
        cursor.close()

        flash("Registered successfully! Please login.", "success")
        return redirect("/hotel_login")

    return render_template("hotel_register.html")


# ==============================
# HOTEL LOGIN
# ==============================
@app.route("/hotel_login", methods=["GET","POST"])
def hotel_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        # First, authenticate the hotel owner by email/password
        cursor.execute(
            "SELECT * FROM hotel_owners WHERE email=%s AND password=%s",
            (email, password)
        )
        owner = cursor.fetchone()

        if owner:
            session["owner_id"] = owner["id"]

            # If this owner already has a linked hotel, check its status
            if owner["hotel_id"]:
                cursor.execute(
                    "SELECT id, status FROM hotels WHERE id=%s",
                    (owner["hotel_id"],)
                )
                hotel = cursor.fetchone()

                if hotel:
                    session["hotel_id"] = hotel["id"]

                    # Allow login even if Pending, but inform the owner
                    if hotel["status"] != "Approved":
                        flash(
                            "Your hotel is not approved by admin yet. "
                            "You can still view and update your details.",
                            "warning"
                        )
                    else:
                        flash("Login successful!", "success")

                    cursor.close()
                    return redirect("/hotel_dashboard")

            # No hotel linked yet – let owner log in and add a hotel
            session["hotel_id"] = None
            flash("Login successful! Please add your hotel details.", "success")
            cursor.close()
            return redirect("/add_hotel")

        # Authentication failed
        flash("Invalid email or password", "danger")
        cursor.close()

    return render_template("hotel_login.html")



# ==============================
# HOTEL DASHBOARD
# ==============================
@app.route("/hotel_dashboard")
def hotel_dashboard():
    if "owner_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get owner details
    cursor.execute("SELECT * FROM hotel_owners WHERE id=%s", (session["owner_id"],))
    owner = cursor.fetchone()
    
    # Get hotel details (may be None for new owners)
    hotel = None
    if session.get("hotel_id"):
        cursor.execute("SELECT * FROM hotels WHERE id=%s", (session["hotel_id"],))
        hotel = cursor.fetchone()

    return render_template("hotel_dashboard.html", hotel=hotel, owner=owner)

@app.route("/hotel_bookings")
def hotel_bookings():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor.execute(
        "SELECT * FROM hotel_bookings WHERE hotel_id=%s ORDER BY check_in DESC",
        (session["hotel_id"],)
    )
    bookings = cursor.fetchall()

    return render_template("hotel_bookings_admin.html", bookings=bookings)

@app.route('/admin/hotel_approvals')
def hotel_approvals():
    cursor = db.cursor(dictionary=True)

    # Pending hotels
    cursor.execute("""
        SELECT h.*, ho.owner_name, ho.email
        FROM hotels h
        LEFT JOIN hotel_owners ho ON h.id = ho.hotel_id
        WHERE h.status='Pending'
    """)
    pending_hotels = cursor.fetchall()

    # Approved hotels
    cursor.execute("""
        SELECT h.*, ho.owner_name, ho.email
        FROM hotels h
        LEFT JOIN hotel_owners ho ON h.id = ho.hotel_id
        WHERE h.status='Approved'
    """)
    approved_hotels = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin_hotel_approvals.html',
        hotels=pending_hotels,
        approved_hotels=approved_hotels
    )



@app.route('/admin/approve_hotel/<int:hotel_id>')
def approve_hotel(hotel_id):
    cursor = db.cursor()

    cursor.execute(
        "UPDATE hotels SET status='Approved' WHERE id=%s",
        (hotel_id,)
    )

    db.commit()
    cursor.close()

    return redirect('/admin/hotel_approvals')

# ==============================
# ADD / UPDATE HOTEL
# ==============================

def parse_price(value: str) -> int:
    """
    Converts inputs like:
    '2500', '2,500', '₹2500', 'Rs. 2,500', 'rupee2500', 'INR 2500'
    into integer 2500
    """
    if not value:
        raise ValueError("Empty price")

    v = value.strip()

    # Remove rupee symbol and spaces
    v = re.sub(r'[₹\s]', '', v)

    # Remove common currency words
    v = re.sub(r'(rupees?|inr|rs\.?)', '', v, flags=re.IGNORECASE)

    # Remove commas
    v = v.replace(",", "")

    # Keep only digits
    v = re.sub(r'[^0-9]', '', v)

    if v == "":
        raise ValueError("Invalid price")

    return int(v)


@app.route("/add_hotel", methods=["GET", "POST"])
def add_hotel():

    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)   # ✅ create cursor here

    if request.method == "POST":
        hotel_name = request.form.get("hotel_name", "").strip()
        place_name = request.form.get("place_name", "").strip()
        spot_name = request.form.get("spot_name", "").strip()
        address = request.form.get("address", "").strip()
        total_rooms = request.form.get("rooms", "").strip()

        # ✅ Price conversion
        try:
            price_per_night = parse_price(request.form.get("price", ""))
        except ValueError:
            flash("Enter valid price like 2500 / 2,500 / ₹2500 / Rs.2500", "danger")
            return redirect("/add_hotel")

        # ✅ Rooms conversion
        try:
            total_rooms = int(total_rooms)
            if total_rooms <= 0:
                raise ValueError
        except ValueError:
            flash("Total rooms must be a valid number!", "danger")
            return redirect("/add_hotel")

        # 1) find place_id from places table using place_name
        cursor.execute("SELECT id FROM places WHERE place_name=%s", (place_name,))
        place = cursor.fetchone()

        if not place:
            flash("Place not found! Add this place in admin first.", "danger")
            return redirect("/add_hotel")

        place_id = place["id"]

        # 2) check if this owner already added a hotel
        cursor.execute("SELECT * FROM hotels WHERE id=%s", (session.get("hotel_id", 0),))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE hotels SET
                    hotel_name=%s,
                    place_id=%s,
                    place_name=%s,
                    spot_name=%s,
                    address=%s,
                    price_per_night=%s,
                    total_rooms=%s,
                    available_rooms=%s,
                    status='Pending'
                WHERE id=%s
            """, (
                hotel_name, place_id, place_name, spot_name, address,
                price_per_night, total_rooms, total_rooms,
                session["hotel_id"]
            ))
            db.commit()
            flash("Hotel updated! Waiting for admin approval.", "success")

        else:
            cursor.execute("""
                INSERT INTO hotels
                (hotel_name, place_id, place_name, spot_name, address,
                 price_per_night, total_rooms, available_rooms, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                hotel_name, place_id, place_name, spot_name, address,
                price_per_night, total_rooms, total_rooms, 'Pending'
            ))
            db.commit()
            
            # Update hotel_owners table to link owner to the new hotel
            new_hotel_id = cursor.lastrowid
            cursor.execute("UPDATE hotel_owners SET hotel_id=%s WHERE id=%s", 
                         (new_hotel_id, session["owner_id"]))
            db.commit()
            
            # Update session with new hotel_id
            session["hotel_id"] = new_hotel_id
            
            flash("Hotel added successfully! Waiting for admin approval.", "success")

        return redirect("/hotel_dashboard")

    return render_template("add_hotel.html")

from datetime import date

def release_expired_rooms():
    cur = db.cursor(dictionary=True)
    today = date.today()

    # Find bookings where checkout date passed
    cur.execute("""
        SELECT hotel_id, SUM(rooms) AS rooms_to_release
        FROM hotel_bookings
        WHERE check_out < %s AND status='Booked'
        GROUP BY hotel_id
    """, (today,))
    rows = cur.fetchall()

    # Restore rooms
    for row in rows:
        cur.execute("""
            UPDATE hotels
            SET available_rooms = available_rooms + %s
            WHERE id=%s
        """, (row["rooms_to_release"], row["hotel_id"]))

    # Mark bookings as completed (optional)
    cur.execute("""
        UPDATE hotel_bookings
        SET status='Cancelled'
        WHERE check_out < %s AND status='Booked'
    """, (today,))

    db.commit()
    cur.close()


@app.route("/search_hotels", methods=["GET"])
def search_hotels():
    if "user_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/login")

    place = request.args.get("place", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    min_rooms = request.args.get("min_rooms", "").strip()
    sort = request.args.get("sort", "price_asc").strip()

    query = """
        SELECT 
            h.*,
            (SELECT image_name FROM hotel_images hi WHERE hi.hotel_id = h.id LIMIT 1) AS image_name
        FROM hotels h
        WHERE h.status='Approved' AND h.available_rooms > 0
    """
    params = []

    # place filter
    if place:
        query += " AND h.place_name LIKE %s"
        params.append(f"%{place}%")

    # price filters
    if min_price:
        query += " AND h.price_per_night >= %s"
        params.append(min_price)

    if max_price:
        query += " AND h.price_per_night <= %s"
        params.append(max_price)

    # rooms filter
    if min_rooms:
        query += " AND h.available_rooms >= %s"
        params.append(min_rooms)

    # sorting
    if sort == "price_desc":
        query += " ORDER BY h.price_per_night DESC"
    elif sort == "rooms_desc":
        query += " ORDER BY h.available_rooms DESC"
    else:
        query += " ORDER BY h.price_per_night ASC"

    cursor.execute(query, tuple(params))
    hotels = cursor.fetchall()

    return render_template(
        "search_hotels.html",
        hotels=hotels,
        place=place,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        sort=sort
    )

@app.route("/hotel_details/<int:hotel_id>")
def hotel_details(hotel_id):
    if "user_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/login")

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM hotels WHERE id=%s AND status='Approved'", (hotel_id,))
    hotel = cur.fetchone()

    if not hotel:
        cur.close()
        flash("Hotel not found!", "danger")
        return redirect(url_for("search_hotels"))

    cur.execute("SELECT * FROM hotel_images WHERE hotel_id=%s", (hotel_id,))
    images = cur.fetchall()
    
    # Map image_name to image_path for template compatibility
    for img in images:
        if 'image_name' in img:
            img['image_path'] = img['image_name']

    cur.close()
    return render_template("view_hotel.html", hotel=hotel, images=images)


@app.route("/hotel/<int:hotel_id>/book", methods=["POST"])
def book_hotel(hotel_id):

    # 🔹 Release expired rooms first
    release_expired_rooms()

    full_name = request.form.get("full_name")
    phone = request.form.get("phone")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    rooms = int(request.form.get("rooms", 1))

    cur = db.cursor(dictionary=True)

    # Get hotel
    cur.execute("SELECT * FROM hotels WHERE id=%s AND status='Approved'", (hotel_id,))
    hotel = cur.fetchone()

    if not hotel:
        cur.close()
        flash("Hotel not found.", "danger")
        return redirect(url_for("search_hotels"))

    # Check room availability
    if rooms > hotel["available_rooms"]:
        cur.close()
        flash("Not enough rooms available!", "warning")
        return redirect(url_for("hotel_details", hotel_id=hotel_id))

    # Calculate nights
    d1 = datetime.strptime(check_in, "%Y-%m-%d")
    d2 = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (d2 - d1).days

    if nights <= 0:
        cur.close()
        flash("Check-out must be after check-in.", "warning")
        return redirect(url_for("hotel_details", hotel_id=hotel_id))

    total_amount = float(hotel["price_per_night"]) * rooms * nights

    # Get user email (optional but recommended)
    cur.execute("SELECT email FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()
    user_email = user["email"] if user else None

    # Insert booking (MATCHES YOUR TABLE STRUCTURE)
    cur.execute("""
        INSERT INTO hotel_bookings
        (user_id, hotel_id, name, email, phone, check_in, check_out, rooms, total_price, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Booked')
    """, (
        session["user_id"],
        hotel_id,
        full_name,
        user_email,
        phone,
        check_in,
        check_out,
        rooms,
        total_amount
    ))

    # Reduce available rooms
    cur.execute("""
        UPDATE hotels
        SET available_rooms = available_rooms - %s
        WHERE id=%s
    """, (rooms, hotel_id))

    db.commit()
    cur.close()

    flash(f"Booking successful! Total amount: ₹{total_amount:.2f}", "success")
    return redirect(url_for("hotel_details", hotel_id=hotel_id))


# ======================================
# USER — VIEW MY HOTEL BOOKINGS
# ======================================
@app.route("/my_hotel_bookings")
def my_hotel_bookings():

    if "user_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/login")

    cur = db.cursor(dictionary=True)

    # Get only this user's bookings
    cur.execute("""
        SELECT 
            hb.id,
            hb.check_in,
            hb.check_out,
            hb.rooms,
            hb.total_price,
            hb.status,
            h.hotel_name,
            h.place_name,
            h.spot_name
        FROM hotel_bookings hb
        LEFT JOIN hotels h ON hb.hotel_id = h.id
        WHERE hb.user_id = %s
        ORDER BY hb.id DESC
    """, (session["user_id"],))

    bookings = cur.fetchall()
    cur.close()

    return render_template("my_hotel_bookings.html", bookings=bookings)


# ==============================
# ADMIN — HOTEL BOOKINGS
# ==============================
@app.route("/admin/hotel_bookings")
def admin_hotel_bookings():

    if "admin_id" not in session:
        flash("Please login as Admin", "warning")
        return redirect("/admin_login")

    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            hb.id,
            hb.check_in,
            hb.check_out,
            hb.rooms,
            hb.total_price,
            hb.status,
            h.hotel_name,
            h.place_name,
            u.name AS user_name,
            u.email,
            hb.phone
        FROM hotel_bookings hb
        LEFT JOIN hotels h ON hb.hotel_id = h.id
        LEFT JOIN users u ON hb.user_id = u.id
        ORDER BY hb.id DESC
    """)

    bookings = cur.fetchall()
    cur.close()

    return render_template("admin_hotel_bookings.html", bookings=bookings)

# ---------------- HOTEL IMAGES MANAGEMENT ----------------
@app.route('/hotel_images', methods=['GET', 'POST'])
def hotel_images():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get hotel details
    cursor.execute("SELECT * FROM hotels WHERE id=%s", (session["hotel_id"],))
    hotel = cursor.fetchone()
    
    # Get owner details
    cursor.execute("SELECT * FROM hotel_owners WHERE id=%s", (session["owner_id"],))
    owner = cursor.fetchone()

    if request.method == 'POST':
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join('static', 'uploads', 'hotels')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Save to database
                cursor.execute("""
                    INSERT INTO hotel_images (hotel_id, image_name) 
                    VALUES (%s, %s)
                """, (session["hotel_id"], filename))
                db.commit()
                
                flash("Image uploaded successfully!", "success")
                return redirect('/hotel_images')

    # Get existing images
    cursor.execute("SELECT * FROM hotel_images WHERE hotel_id=%s", (session["hotel_id"],))
    images = cursor.fetchall()
    
    # Update image data to use correct column name
    for img in images:
        if 'image_path' not in img and 'image_name' in img:
            img['image_path'] = img['image_name']
        elif 'image_path' not in img and 'image' in img:
            img['image_path'] = img['image']
        elif 'image_path' not in img and 'filename' in img:
            img['image_path'] = img['filename']

    return render_template("hotel_images.html", hotel=hotel, owner=owner, images=images)

@app.route('/delete_hotel_image/<int:image_id>', methods=['POST'])
def delete_hotel_image(image_id):
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get image details
    cursor.execute("SELECT * FROM hotel_images WHERE id=%s", (image_id,))
    image = cursor.fetchone()
    
    if image:
        # Delete file from filesystem
        try:
            # Use the correct column name
            filename = image.get('image_path') or image.get('image_name') or image.get('image') or image.get('filename')
            if filename:
                file_path = os.path.join('static', 'uploads', 'hotels', filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        except:
            pass
        
        # Delete from database
        cursor.execute("DELETE FROM hotel_images WHERE id=%s", (image_id,))
        db.commit()
        
        flash("Image deleted successfully!", "success")
    
    return redirect('/hotel_images')

@app.route('/hotel_revenue')
def hotel_revenue():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get owner details
    cursor.execute("SELECT * FROM hotel_owners WHERE id=%s", (session["owner_id"],))
    owner = cursor.fetchone()

    # Calculate revenue from bookings
    cursor.execute("""
        SELECT SUM(total_price) as total_revenue, 
               COUNT(*) as total_bookings,
               MONTH(check_in) as month
        FROM hotel_bookings 
        WHERE hotel_id=%s AND status='Booked'
        GROUP BY MONTH(check_in)
        ORDER BY month DESC
    """, (session["hotel_id"],))
    
    revenue_data = cursor.fetchall()
    
    # Get total revenue
    cursor.execute("""
        SELECT SUM(total_price) as total_revenue, COUNT(*) as total_bookings
        FROM hotel_bookings 
        WHERE hotel_id=%s AND status='Booked'
    """, (session["hotel_id"],))
    
    total_stats = cursor.fetchone()

    return render_template("hotel_revenue.html", owner=owner, revenue_data=revenue_data, total_stats=total_stats)

@app.route('/manage_rooms')
def manage_rooms():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get owner details
    cursor.execute("SELECT * FROM hotel_owners WHERE id=%s", (session["owner_id"],))
    owner = cursor.fetchone()
    
    # Get hotel details
    cursor.execute("SELECT * FROM hotels WHERE id=%s", (session["hotel_id"],))
    hotel = cursor.fetchone()

    return render_template("manage_rooms.html", owner=owner, hotel=hotel)

@app.route('/update_rooms', methods=['POST'])
def update_rooms():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    available_rooms = request.form.get('available_rooms')
    total_rooms = request.form.get('total_rooms')

    cursor = db.cursor()
    
    cursor.execute("""
        UPDATE hotels 
        SET available_rooms=%s, total_rooms=%s 
        WHERE id=%s
    """, (available_rooms, total_rooms, session["hotel_id"]))
    
    db.commit()
    flash("Room information updated successfully!", "success")
    return redirect('/manage_rooms')

@app.route('/hotel_profile')
def hotel_profile():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    cursor = db.cursor(dictionary=True)
    
    # Get owner details
    cursor.execute("SELECT * FROM hotel_owners WHERE id=%s", (session["owner_id"],))
    owner = cursor.fetchone()
    
    # Get hotel details
    cursor.execute("SELECT * FROM hotels WHERE id=%s", (session["hotel_id"],))
    hotel = cursor.fetchone()

    return render_template("hotel_profile.html", owner=owner, hotel=hotel)

@app.route('/update_hotel_profile', methods=['POST'])
def update_hotel_profile():
    if "hotel_id" not in session:
        flash("Please login first!", "warning")
        return redirect("/hotel_login")

    hotel_name = request.form.get('hotel_name')
    address = request.form.get('address')
    price_per_night = request.form.get('price_per_night')

    cursor = db.cursor()
    
    cursor.execute("""
        UPDATE hotels 
        SET hotel_name=%s, address=%s, price_per_night=%s 
        WHERE id=%s
    """, (hotel_name, address, price_per_night, session["hotel_id"]))
    
    db.commit()
    flash("Hotel profile updated successfully!", "success")
    return redirect('/hotel_profile')



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
    
