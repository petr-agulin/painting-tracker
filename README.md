⚠️ Work in Progress — This project is under development. Contributions are welcome later, the code is unfinished.

# 🎨 Painting Tracker

A personal painting session tracker built for watercolor artists.

Log every painting session, track your progress, discover patterns in your creative process, and build a visual archive of your work — all stored privately on your own computer.

---

## What it does

- **Log paintings** — record subject, style, inspiration source, paper, mood, and more
- **Log sessions** — track time, techniques, colors used, mental state, what worked and what didn't
- **Visual palette** — build your personal paint collection from a database of 200+ professional watercolor paints across Schmincke Horadam, Winsor & Newton, Daniel Smith, Holbein, and Sennelier
- **Progress timeline** — see a painting evolve session by session with photos and notes
- **Next up inbox** — see all in-progress paintings sorted by last session date so nothing gets forgotten
- **Insights dashboard** — discover patterns in your painting habits after months of data
- **Personal records** — track total hours painted, best streaks, longest sessions
- **Export** — download any painting's full history as a CSV file

---

## Requirements

- Windows or Mac computer
- Internet connection for the one-time setup only

---

## Installation and setup — Windows

1. Install Python from **https://python.org/downloads**
   - During installation, check the box that says **Add Python to PATH**
2. Download this project by clicking the green **Code** button above, then **Download ZIP**
3. Unzip the downloaded file to a folder on your computer
4. Double-click **start_windows.bat**
5. The app will open in your browser automatically

---

## Installation and setup — Mac

1. Install Python from **https://python.org/downloads**
2. Download this project by clicking the green **Code** button above, then **Download ZIP**
3. Unzip the downloaded file to a folder on your computer
4. Right-click **start_mac.command** and select **Open**
   - If Mac warns you about an unidentified developer, go to System Preferences → Security and click **Open Anyway**
5. The app will open in your browser automatically

---

## After setup

Every time you want to use the app, just double-click the launcher file. No terminal needed.

Your data is stored in a file called `painting_tracker.db` inside the `data` folder. This file belongs to you — back it up like any important document.

---

## About the paint color database

The app includes a database of 200+ watercolor paints with color swatches to help you quickly log which colors you used in each session.

Note: The hex color codes in this database are pigment-based approximations, not scientifically measured values. Colors are derived from the known spectral properties of each paint's pigments and are intended as a visual reference only. Your actual paint on paper may differ slightly depending on dilution, paper type, and lighting conditions. You can correct any color manually using the built-in color picker in the Palette page.

---

## How color mixing works

The Log Session page includes a color finder that suggests how to mix a target color using paints from your personal palette.

The mixing algorithm uses the **Kubelka-Munk model** — a physical model developed for predicting how pigments mix when applied as a layer on a surface. Unlike simple RGB averaging (which models how light mixes on screens), Kubelka-Munk models subtractive mixing, which is how physical paint actually behaves. This means, for example, that yellow and blue will correctly predict green rather than a muddy gray.

The algorithm converts each paint's color into absorption and scattering ratios, mixes those in the proportions being tested, then converts the result back to a visible color. To find the best proportions, it uses a continuous mathematical optimizer (scipy SLSQP) rather than stepping through fixed increments — which gives more precise ratios and runs faster on large palettes.

The result is shown as a "Mix result" swatch next to the "Target" swatch, so you can see at a glance how close the predicted mix gets to the color you are trying to achieve.

Note: the model works best with measured pigment data. Since the paint database uses approximate hex codes rather than laboratory-measured values, the suggestions are a useful starting point for real experimentation rather than an exact prescription.

---

## Adding paints to your palette

1. Go to the **Palette** page in the sidebar
2. Select your brand and search by color name or the number printed on your tube
3. Click **Add to my palette**
4. Your paint will appear as a colored swatch when logging sessions

If your paint is not in the database, use the **Add Manually** tab and pick the color visually.

---

## Built with

- Python
- Streamlit
- SQLite
- Plotly
- Pandas

---

## About

Built by a watercolor painter who is also a product manager learning to code. If you find this useful, have suggestions, or want to contribute, feel free to open an issue or pull request on GitHub.
