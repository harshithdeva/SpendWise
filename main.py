from flask import Flask, render_template, request, redirect, flash, jsonify, session
from flask_login import (
    LoginManager,
    login_required,
    login_user,
    logout_user,
    current_user,
    UserMixin,
)
import os
from datetime import timedelta  # used for setting session timeout
import pandas as pd
import plotly
import plotly.express as px
import json
import warnings
import support

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=20)  # Set session lifetime
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Name of your login route


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


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/login_validation", methods=["POST"])
def login_validation():
    if not current_user.is_authenticated:
        email = request.form.get("email")
        passwd = request.form.get("password")
        query = "SELECT * FROM user_login WHERE email = ? AND password = ?"
        users = support.execute_query("search", query, (email, passwd))
        if len(users) > 0:
            user_obj = User(id=users[0][0], username=users[0][1], email=users[0][2])
            login_user(user_obj)
            session.permanent = True
            flash("Successfully logged in!")
            return redirect("/home")
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
    userdata = support.execute_query(
        "search", "select * from user_login where email = ?", (email,)
    )
    if len(userdata) > 0:
        try:
            query = "update user_login set password = ? where email = ?"
            support.execute_query("insert", query, (pswd, email))
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
    return render_template("register.html")


@app.route("/registration", methods=["POST"])
def registration():
    name = request.form.get("name")
    email = request.form.get("email")
    passwd = request.form.get("password")
    if (
        len(name) > 5 and len(email) > 10 and len(passwd) > 5
    ):  # if input details satisfy length condition
        try:
            query = "INSERT INTO user_login(username, email, password) VALUES(?,?,?)"
            support.execute_query("insert", query, (name, email, passwd))

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

    table_query = "select * from user_expenses where user_id = ? order by pdate desc"
    table_data = support.execute_query("search", table_query, (user_id,))
    df = pd.DataFrame(
        table_data, columns=["#", "User_Id", "Date", "Expense", "Amount", "Note"]
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
        df_size=df.shape[0],
        df=jsonify(df.to_json()),
        earning=earning,
        spend=spend,
        invest=invest,
        saving=saving,
        monthly_data=monthly_data,
        card_data=card_data,
        goals=goals,
        table_data=table_data[:4],
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


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
