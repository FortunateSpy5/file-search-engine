// JSON Server -> Dummy Database and Backend
// npm install -g json-server
// json-server --watch db.json

const express = require("express");
const axios = require("axios");
var jwt = require("jsonwebtoken");

const secret = "secret";

const app = express();

app.get("/users", (req, res) => {
	axios
		.get("http://localhost:3000/users")
		.then((response) => {
			data = jwt.verify(req.query.token, secret);
			flag = false;
			response.data.forEach((user) => {
				if (
					user.username === data.username &&
					user.password === data.password
				) {
					res.send({
						id: user["id"],
						permissions: user["permissions"],
					});
					flag = true;
				}
			});
			if (!flag)
				res.status(401).send("Either username or password is wrong.");
		})
		.catch((err) => {
			res.status(500).send(err);
		});
});

app.post("/users", (req, res) => {
	data = jwt.verify(req.query.token, secret);
	axios
		.post("http://localhost:3000/users", data)
		.then((response) => {
			res.send(response.data);
		})
		.catch((err) => {
			res.status(500).send(err);
		});
});

app.put("/users", (req, res) => {
	data = jwt.verify(req.query.token, secret);
	axios
		.put("http://localhost:3000/users/" + data.id, data)
		.then((response) => {
			res.send(response.data);
		})
		.catch((err) => {
			res.status(500).send(err);
		});
});

console.log("Listening on port 3001");
app.listen(3001);
