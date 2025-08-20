import os
import io
import threading
import requests
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox

# ======================== CONFIG ========================
API_KEY = os.getenv("OWM_API_KEY", "OWM_API_KEY")  # <- put your key or set OWM_API_KEY
API_URL = "https://api.openweathermap.org/data/2.5/weather"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@2x.png"
TIMEOUT = 10
# ========================================================

class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WeatherNow — Clean Desktop Weather")
        self.geometry("520x420")
        self.resizable(False, False)

        # State
        self.icon_image = None
        self.units_var = tk.StringVar(value="metric")  # metric=f°, imperial=°F
        self.city_var = tk.StringVar()

        # Styles
        style = ttk.Style(self)
        try:
            self.tk.call("tk", "scaling", 1.2)  # slightly larger UI
        except Exception:
            pass
        style.configure("TFrame", padding=12)
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 13))
        style.configure("TButton", padding=6)
        style.configure("Card.TFrame", relief="groove", borderwidth=1, padding=12)

        # Layout
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(container)
        header.pack(fill="x")
        ttk.Label(header, text="WeatherNow", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="  •  Real-time weather via OpenWeatherMap").pack(side="left")

        # Input row
        input_row = ttk.Frame(container)
        input_row.pack(fill="x", pady=(8, 4))

        city_entry = ttk.Entry(input_row, textvariable=self.city_var, width=28, font=("Segoe UI", 11))
        city_entry.pack(side="left", padx=(0, 8))
        city_entry.bind("<Return>", lambda e: self.fetch_weather())

        ttk.Button(input_row, text="Get Weather", command=self.fetch_weather).pack(side="left")

        units_box = ttk.Frame(input_row)
        units_box.pack(side="right")
        ttk.Radiobutton(units_box, text="°C", variable=self.units_var, value="metric").pack(side="left", padx=4)
        ttk.Radiobutton(units_box, text="°F", variable=self.units_var, value="imperial").pack(side="left", padx=4)

        # Card
        card = ttk.Frame(container, style="Card.TFrame")
        card.pack(fill="both", expand=True, pady=(8, 0))

        # City + description
        self.city_label = ttk.Label(card, text="Enter a city and press Get Weather", style="Title.TLabel")
        self.city_label.pack(anchor="w")

        # Icon + main metrics
        top_row = ttk.Frame(card)
        top_row.pack(fill="x", pady=8)

        self.icon_label = ttk.Label(top_row)
        self.icon_label.pack(side="left", padx=(0, 12))

        metrics_frame = ttk.Frame(top_row)
        metrics_frame.pack(side="left", fill="x", expand=True)

        self.temp_label = ttk.Label(metrics_frame, text="Temp: —")
        self.temp_label.pack(anchor="w")
        self.feels_label = ttk.Label(metrics_frame, text="Feels like: —")
        self.feels_label.pack(anchor="w")
        self.desc_label = ttk.Label(metrics_frame, text="Conditions: —")
        self.desc_label.pack(anchor="w")

        # Extra details grid
        grid = ttk.Frame(card)
        grid.pack(fill="x", pady=(6, 0))

        self.details = {
            "humidity": ttk.Label(grid, text="Humidity: —"),
            "wind": ttk.Label(grid, text="Wind: —"),
            "pressure": ttk.Label(grid, text="Pressure: —"),
            "clouds": ttk.Label(grid, text="Clouds: —"),
        }

        # 2x2 grid layout
        self.details["humidity"].grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.details["wind"].grid(row=0, column=1, sticky="w", padx=2, pady=2)
        self.details["pressure"].grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.details["clouds"].grid(row=1, column=1, sticky="w", padx=2, pady=2)

        # Status bar
        self.status = ttk.Label(self, text="", anchor="w")
        self.status.pack(fill="x", side="bottom")

        # Prefill example
        self.city_var.set("Mumbai")

    def fetch_weather(self):
        city = self.city_var.get().strip()
        if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
            messagebox.showwarning("API Key Required",
                                   "Please set your OpenWeatherMap API key in the code or OWM_API_KEY env var.")
            return
        if not city:
            messagebox.showinfo("City Required", "Please enter a city name.")
            return

        self.set_status(f"Fetching weather for {city}…")
        # Use a thread so UI stays responsive
        threading.Thread(target=self._do_fetch, args=(city, self.units_var.get()), daemon=True).start()

    def _do_fetch(self, city: str, units: str):
        try:
            params = {"q": city, "appid": API_KEY, "units": units}
            r = requests.get(API_URL, params=params, timeout=TIMEOUT)
            if r.status_code != 200:
                try:
                    data = r.json()
                    msg = data.get("message", "Unknown error")
                except Exception:
                    msg = f"HTTP {r.status_code}"
                self._after_error(f"Failed to fetch weather: {msg.capitalize()}")
                return
            data = r.json()
            self._after_success(data, units)
        except requests.exceptions.RequestException as e:
            self._after_error(f"Network error: {e}")

    def _after_success(self, data, units):
        self.after(0, lambda: self._update_ui(data, units))

    def _after_error(self, msg):
        self.after(0, lambda: (self.set_status(""), messagebox.showerror("Error", msg)))

    def _update_ui(self, data, units):
        # City & country
        city_name = data.get("name", "—")
        sys = data.get("sys", {})
        country = sys.get("country", "")
        self.city_label.config(text=f"{city_name}, {country}".strip(", "))

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        weather_list = data.get("weather", [])
        weather = weather_list[0] if weather_list else {}

        unit_symbol = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"

        temp = main.get("temp", "—")
        feels = main.get("feels_like", "—")
        desc = weather.get("description", "—").title()

        self.temp_label.config(text=f"Temp: {temp}{unit_symbol}")
        self.feels_label.config(text=f"Feels like: {feels}{unit_symbol}")
        self.desc_label.config(text=f"Conditions: {desc}")

        self.details["humidity"].config(text=f"Humidity: {main.get('humidity', '—')}%")
        self.details["wind"].config(text=f"Wind: {wind.get('speed', '—')} {speed_unit}")
        self.details["pressure"].config(text=f"Pressure: {main.get('pressure', '—')} hPa")
        self.details["clouds"].config(text=f"Clouds: {clouds.get('all', '—')}%")

        # Load icon
        icon_code = weather.get("icon")
        if icon_code:
            try:
                img_bytes = requests.get(ICON_URL.format(icon=icon_code), timeout=TIMEOUT).content
                pil_img = Image.open(io.BytesIO(img_bytes))
                self.icon_image = ImageTk.PhotoImage(pil_img)
                self.icon_label.config(image=self.icon_image)
            except Exception:
                self.icon_label.config(image="")
        else:
            self.icon_label.config(image="")

        self.set_status("")

    def set_status(self, text: str):
        self.status.config(text=text)


if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()
