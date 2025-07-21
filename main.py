import email
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    jsonify,
    session,
    send_file,
)
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
    current_user,
    UserMixin,
)
from flask_wtf import CSRFProtect
import os
import io
import csv
import requests
from datetime import timedelta  # used for setting session timeout
import pandas as pd
import plotly
import plotly.express as px
import json
from datetime import datetime
import warnings
import support
from werkzeug.security import generate_password_hash, check_password_hash

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=20)  # Set session lifetime
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Name of your login route
csrf = CSRFProtect(app)
RECAPTCHA_ENABLED = os.environ.get("RECAPTCHA_ENABLED", "1") == "1"


class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    query = "SELECT * FROM user_login WHERE user_id = ?"
    user = support.execute_query("search", query, (user_id,))
    if user:
        return User(id=user[0][0], username=user[0][1], email=user[0][2])
    return None


def verify_recaptcha():
    if not RECAPTCHA_ENABLED:
        return True  # Skip verification if disabled
    recaptcha_response = request.form.get("g-recaptcha-response")
    secret_key = os.environ.get("RECAPTCHA_SECRET_KEY")
    payload = {"secret": secret_key, "response": recaptcha_response}
    r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
    result = r.json()
    return result.get("success", False)


@app.route("/")
def login():
    site_key = os.environ.get("RECAPTCHA_SITE_KEY")
    recaptcha_enabled = RECAPTCHA_ENABLED
    return render_template(
        "login.html", recaptcha_site_key=site_key, recaptcha_enabled=recaptcha_enabled
    )


@app.route("/login_validation", methods=["POST"])
def login_validation():
    if not verify_recaptcha():
        flash("reCAPTCHA verification failed. Please try again.")
        return redirect("/")
    if not current_user.is_authenticated:
        email = request.form.get("email")
        passwd = request.form.get("password")
        query = "SELECT * FROM user_login WHERE email = ?"
        users = support.execute_query("search", query, (email,))
        if users:
            user_obj = User(id=users[0][0], username=users[0][1], email=users[0][2])
            hashed_password = users[0][3]
            if check_password_hash(hashed_password, passwd):
                login_user(user_obj)
                session.permanent = True
                flash("Successfully logged in!")
                return redirect("/home")
            else:
                flash("Invalid email and password!")
                return redirect("/")
        else:
            flash("Invalid email and password!")
            return redirect("/")
    else:
        flash("Already a user is logged-in!")
        return redirect("/home")


@app.route("/reset", methods=["POST"])
def reset():
    email = request.form.get("femail")
    pswd = request.form.get("pswd")
    hashed_password = generate_password_hash(pswd)
    userdata = support.execute_query(
        "search", "select * from user_login where email = ?", (email,)
    )
    if len(userdata) > 0:
        try:
            query = "update user_login set password = ? where email = ?"
            support.execute_query("insert", query, (hashed_password, email))
            flash("Password has been changed!!")
            return redirect("/")
        except:
            flash("Something went wrong!!")
            return redirect("/")
    else:
        flash("Invalid email address!!")
        return redirect("/")


@app.route("/register")
def register():
    site_key = os.environ.get("RECAPTCHA_SITE_KEY")
    return render_template(
        "register.html",
        recaptcha_site_key=site_key,
        recaptcha_enabled=RECAPTCHA_ENABLED,
    )


@app.route("/registration", methods=["POST"])
def registration():
    if not verify_recaptcha():
        flash("reCAPTCHA verification failed. Please try again.")
        return redirect("/register")
    name = request.form.get("name")
    email = request.form.get("email")
    passwd = request.form.get("password")
    hashed_password = generate_password_hash(passwd)
    if (
        len(name) > 5 and len(email) > 10 and len(passwd) > 5
    ):  # if input details satisfy length condition
        try:
            query = "INSERT INTO user_login(username, email, password) VALUES(?,?,?)"
            support.execute_query("insert", query, (name, email, hashed_password))

            user = support.execute_query(
                "search",
                "SELECT * from user_login where email = ?",
                (email,),
            )
            user_obj = User(id=user[0][0], username=user[0][1], email=user[0][2])
            login_user(user_obj)
            flash("Successfully Registered!!")
            return redirect("/home")
        except:
            flash("Email id already exists, use another email!!")
            return redirect("/register")
    else:  # if input condition length not satisfy
        flash("Not enough data to register, try again!!")
        return redirect("/register")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/feedback", methods=["POST"])
def feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    sub = request.form.get("sub")
    message = request.form.get("message")
    flash("Thanks for reaching out to us. We will contact you soon.")
    return redirect("/")


@app.route("/home")
@login_required
def home():
    user_id = current_user.id
    query = "select * from user_login where user_id = ?"
    userdata = support.execute_query("search", query, (user_id,))
    page = int(request.args.get("page", 1))
    per_page = int(
        request.args.get("per_page", 5)
    )  # Get per_page from query, default 5
    offset = (page - 1) * per_page

    table_query = "SELECT * FROM user_expenses WHERE user_id = ? ORDER BY pdate DESC LIMIT ? OFFSET ?"
    table_data = support.execute_query(
        "search", table_query, (user_id, per_page, offset)
    )

    count_query = "SELECT COUNT(*) FROM user_expenses WHERE user_id = ?"
    total_count = support.execute_query("search", count_query, (user_id,))[0][0]
    total_pages = (total_count + per_page - 1) // per_page

    # Calling a full query to build the DataFrame and charts
    full_table_query = (
        "SELECT * FROM user_expenses WHERE user_id = ? ORDER BY pdate DESC"
    )
    full_table_data = support.execute_query("search", full_table_query, (user_id,))

    df = pd.DataFrame(
        full_table_data, columns=["#", "User_Id", "Date", "Expense", "Amount", "Note"]
    )

    df = support.generate_df(df)
    try:
        earning, spend, invest, saving = support.top_tiles(df)
    except:
        earning, spend, invest, saving = 0, 0, 0, 0

    try:
        bar, pie, line, stack_bar = support.generate_Graph(df)
    except Exception as e:
        print("⚠️ Error generating charts:", e)
        bar, pie, line, stack_bar = None, None, None, None
    try:
        monthly_data = support.get_monthly_data(df, res=None)
    except:
        monthly_data = []
    try:
        card_data = support.sort_summary(df)
    except:
        card_data = []

    try:
        goals = support.expense_goal(df)
    except:
        goals = []
    try:
        size = 240
        pie1 = support.makePieChart(df, "Earning", "Month_name", size=size)
        pie2 = support.makePieChart(df, "Spend", "Day_name", size=size)
        pie3 = support.makePieChart(df, "Investment", "Year", size=size)
        pie4 = support.makePieChart(df, "Saving", "Note", size=size)
        pie5 = support.makePieChart(df, "Saving", "Day_name", size=size)
        pie6 = support.makePieChart(df, "Investment", "Note", size=size)
    except:
        pie1, pie2, pie3, pie4, pie5, pie6 = None, None, None, None, None, None
    return render_template(
        "home.html",
        user_name=userdata[0][1],
        table_data=table_data,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        df_size=df.shape[0],
        df=jsonify(df.to_json()),
        earning=earning,
        spend=spend,
        invest=invest,
        saving=saving,
        monthly_data=monthly_data,
        card_data=card_data,
        goals=goals,
        bar=bar,
        line=line,
        stack_bar=stack_bar,
        pie1=pie1,
        pie2=pie2,
        pie3=pie3,
        pie4=pie4,
        pie5=pie5,
        pie6=pie6,
    )


@app.route("/home/add_expense", methods=["POST"])
@login_required
def add_expense():
    user_id = current_user.id
    if request.method == "POST":
        date = request.form.get("e_date")
        expense = request.form.get("e_type")
        amount = request.form.get("amount")
        notes = request.form.get("notes")
        try:
            query = """insert into user_expenses (user_id, pdate, expense, amount, pdescription) values (?, ?, ?, ?, ?)"""
            support.execute_query(
                "insert", query, (user_id, date, expense, amount, notes)
            )
            flash("Saved!!")
        except:
            flash("Something went wrong.")
            return redirect("/home")
        return redirect("/home")


@app.route("/api/expense/delete/<int:expense_id>", methods=["POST"])
@login_required
def api_delete_expense(expense_id):
    # Check if expense exists for this user
    query_check = "SELECT id FROM user_expenses WHERE id=? AND user_id=?"
    result = support.execute_query("search", query_check, (expense_id, current_user.id))
    if not result:
        return jsonify({"success": False, "message": "Expense not found."}), 404

    # Proceed to delete
    query = "DELETE FROM user_expenses WHERE id=? AND user_id=?"
    support.execute_query("insert", query, (expense_id, current_user.id))
    return jsonify({"success": True, "message": "Expense deleted."}), 200


@app.route("/api/expense/edit/<int:expense_id>", methods=["POST"])
@login_required
def api_edit_expense(expense_id):
    data = request.get_json()
    date = data.get("date")
    expense = data.get("expense")
    amount = data.get("amount")
    note = data.get("note")

    # Validate required fields
    if not date or not expense or not amount:
        return jsonify({"success": False, "message": "Missing required fields."}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return (
            jsonify({"success": False, "message": "Amount must be a positive number."}),
            400,
        )

    # Check if expense exists for this user
    query_check = "SELECT id FROM user_expenses WHERE id=? AND user_id=?"
    result = support.execute_query("search", query_check, (expense_id, current_user.id))
    if not result:
        return jsonify({"success": False, "message": "Expense not found."}), 404

    # Proceed to update
    query = """
        UPDATE user_expenses
        SET pdate=?, expense=?, amount=?, pdescription=?
        WHERE id=? AND user_id=?
    """
    support.execute_query(
        "insert", query, (date, expense, amount, note, expense_id, current_user.id)
    )
    return jsonify({"success": True, "message": "Expense updated."}), 200


@app.route("/analysis")
@login_required
def analysis():
    user_id = current_user.id
    query = "select * from user_login where user_id = ?"
    userdata = support.execute_query("search", query, (user_id,))
    query2 = "select pdate,expense, pdescription, amount from user_expenses where user_id = ?"
    data = support.execute_query("search", query2, (user_id,))
    df = pd.DataFrame(data, columns=["Date", "Expense", "Note", "Amount"])
    df = support.generate_df(df)

    if df.shape[0] > 0:
        pie = support.meraPie(
            df=df,
            names="Expense",
            values="Amount",
            hole=0.7,
            hole_text="Expense",
            hole_font=20,
            height=180,
            width=180,
            margin=dict(t=1, b=1, l=1, r=1),
        )
        df2 = df.groupby(["Note", "Expense"])[["Amount"]].sum().reset_index()
        bar = support.meraBarChart(
            df=df2,
            x="Note",
            y="Amount",
            color="Expense",
            height=180,
            x_label="Category",
            show_xtick=False,
        )
        line = support.meraLine(
            df=df,
            x="Date",
            y="Amount",
            color="Expense",
            slider=False,
            show_legend=False,
            height=180,
        )
        scatter = support.meraScatter(
            df,
            "Date",
            "Amount",
            "Expense",
            "Amount",
            slider=False,
        )
        heat = support.meraHeatmap(
            df,
            "Day_name",
            "Month_name",
            height=200,
            title="Transaction count Day vs Month",
        )
        month_bar = support.month_bar(df, 280)
        sun = support.meraSunburst(df, 280)

        return render_template(
            "analysis.html",
            user_name=userdata[0][1],
            pie=pie,
            bar=bar,
            line=line,
            scatter=scatter,
            heat=heat,
            month_bar=month_bar,
            sun=sun,
        )
    else:
        flash("No data records to analyze.")
        return redirect("/home")


@app.route("/profile")
@login_required
def profile():
    user_id = current_user.id
    query = "select * from user_login where user_id = ?"
    userdata = support.execute_query("search", query, (user_id,))
    return render_template(
        "profile.html", user_name=userdata[0][1], email=userdata[0][2]
    )


@app.route("/updateprofile", methods=["POST"])
@login_required
def update_profile():
    user_id = current_user.id
    name = request.form.get("name")
    email = request.form.get("email")
    query = "select * from user_login where user_id = ?"
    userdata = support.execute_query("search", query, (user_id,))
    query = "select * from user_login where email = ?"
    email_list = support.execute_query("search", query, (email,))
    if name != userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = "update user_login set username = ?, email = ? where user_id = ?"
        support.execute_query("insert", query, (name, email, user_id))
        flash("Name and Email updated!!")
        return redirect("/profile")
    elif name != userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect("/profile")
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = "update user_login set email = ? where user_id = ?"
        support.execute_query("insert", query, (email, user_id))
        flash("Email updated!!")
        return redirect("/profile")
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect("/profile")

    elif name != userdata[0][1] and email == userdata[0][2]:
        query = "update user_login set username = ? where user_id = ?"
        support.execute_query("insert", query, (name, user_id))
        flash("Name updated!!")
        return redirect("/profile")
    else:
        flash("No Change!!")
        return redirect("/profile")


@app.route("/transactions_report", methods=["GET", "POST"])
@login_required
def export_transactions():

    if request.method == "GET":
        # Render the export page with a form to select date range
        return render_template("export_page.html")
    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        user_id = current_user.id

        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                flash("Start date must be before or equal to end date.")
                return redirect("/export_page")
        except Exception:
            flash("Invalid date format.")
            return redirect("/export_page")

        # Query transactions in range
        query = """
            SELECT pdate, expense, amount, pdescription
            FROM user_expenses
            WHERE user_id = ? AND pdate BETWEEN ? AND ?
            ORDER BY pdate DESC
        """
        transactions = support.execute_query(
            "search", query, (user_id, start_date, end_date)
        )

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Expense", "Amount", "Note"])
        for row in transactions:
            writer.writerow(row)
        output.seek(0)

        # Send as downloadable file
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"transactions_{start_date}_to_{end_date}.csv",
        )
    return redirect("/export_page")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
