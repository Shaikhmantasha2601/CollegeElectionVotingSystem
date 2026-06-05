from flask import Flask, render_template, request, redirect
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS parties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_name TEXT NOT NULL,
        features TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_name TEXT UNIQUE,
        voter_type TEXT,
        points INTEGER,
        party_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM parties")
    parties = cur.fetchall()
    conn.close()
    return render_template("index.html", parties=parties)

@app.route("/register_party", methods=["GET", "POST"])
def register_party():
    if request.method == "POST":
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO parties(party_name, features) VALUES (?, ?)",
            (request.form["party_name"], request.form["features"])
        )
        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("register_party.html")

@app.route("/delete_party/<int:party_id>")
def delete_party(party_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM votes WHERE party_id=?", (party_id,))
    cur.execute("DELETE FROM parties WHERE id=?", (party_id,))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        voter_name = request.form["voter_name"]
        voter_type = request.form["voter_type"]

        return redirect(
            f"/select_party?voter_name={voter_name}&voter_type={voter_type}"
        )

    return render_template("voter_info.html")

@app.route("/select_party", methods=["GET", "POST"])
def select_party():
    voter_name = request.args.get("voter_name")
    voter_type = request.args.get("voter_type")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM parties")
    parties = cur.fetchall()

    if request.method == "POST":
        party_id = request.form["party_id"]

        if voter_type == "Teacher":
            points = 20
        elif voter_type == "Student":
            points = 10
        else:
            points = 5

        try:
            cur.execute(
                """
                INSERT INTO votes(voter_name, voter_type, points, party_id)
                VALUES (?, ?, ?, ?)
                """,
                (voter_name, voter_type, points, party_id)
            )

            conn.commit()
            conn.close()

            return render_template("vote_success.html")

        except sqlite3.IntegrityError:
            conn.close()
            return """
            <h2>You have already voted!</h2>
            <br>
            <a href="/">Back To Dashboard</a>
            """

    conn.close()
    return render_template("select_party.html", parties=parties)

@app.route("/results")
def results():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT parties.id,
           parties.party_name,
           COALESCE(SUM(votes.points), 0)
    FROM parties
    LEFT JOIN votes
    ON parties.id = votes.party_id
    GROUP BY parties.id
    ORDER BY COALESCE(SUM(votes.points), 0) DESC
    """)

    results = cur.fetchall()
    conn.close()

    labels = []
    values = []

    for result in results:
        if result[2] > 0:
            labels.append(result[1])
            values.append(result[2])

    chart_exists = False

    if values:
        plt.figure(figsize=(6, 6))
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Election Results")
        plt.savefig("static/results_pie.png", bbox_inches="tight")
        plt.close()
        chart_exists = True

    return render_template(
        "results.html",
        results=results,
        chart_exists=chart_exists
    )

@app.route("/party_voters/<int:party_id>")
def party_voters(party_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT party_name FROM parties WHERE id=?",
        (party_id,)
    )
    party = cur.fetchone()

    cur.execute(
        """
        SELECT voter_name, voter_type, points
        FROM votes
        WHERE party_id=?
        ORDER BY voter_type, voter_name
        """,
        (party_id,)
    )
    voters = cur.fetchall()

    conn.close()

    return render_template(
        "party_voters.html",
        party=party,
        voters=voters
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
