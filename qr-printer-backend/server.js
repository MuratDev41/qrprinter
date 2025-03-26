const express = require("express");
const multer = require("multer");
const cors = require("cors");
const path = require("path");
const fs = require("fs");

const app = express();
app.use(cors());
app.use(express.json());

const uploadDir = path.join(__dirname, "uploads");
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  },
});

const upload = multer({ storage });

app.post("/upload", upload.single("file"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ message: "No file uploaded" });
  }
  res.json({ message: "File uploaded successfully", filename: req.file.filename, path: `/uploads/${req.file.filename}` });
});

app.use("/uploads", express.static(uploadDir));


app.get("/files", (req, res) => {
  fs.readdir(uploadDir, (err, files) => {
    if (err) {
      return res.status(500).json({ message: "Error reading files" });
    }
    const fileList = files.map(file => ({ filename: file, path: `/uploads/${file}` }));
    res.json(fileList);
  });
});

app.use("/uploads", express.static(uploadDir));

app.listen(5000, () => console.log("Server running on port 5000"));
