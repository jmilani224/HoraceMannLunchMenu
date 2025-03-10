const fetch = require("node-fetch");
const fs = require("fs");

const url = "https://www.myschoolmenus.com/api/v1/public/menu/74432";
const headers = { "x-district": "1543" };

async function updateMenu() {
    try {
        const response = await fetch(url, { headers });
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();

        if (!data || !data.data || !data.data.days) throw new Error("Unexpected API response format");

        let calendarData = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//School Menu//EN\n";
        
        data.data.days.forEach(day => {
            if (!day.date || !day.menu_items) return;
            const date = day.date.replace(/-/g, '');
            day.menu_items.forEach(item => {
                if (!item.name) return;
                calendarData += `BEGIN:VEVENT\nSUMMARY:${item.name}\nDTSTART;VALUE=DATE:${date}\nDTEND;VALUE=DATE:${date}\nEND:VEVENT\n`;
            });
        });

        calendarData += "END:VCALENDAR";

        fs.writeFileSync("school_menu.ics", calendarData);
        console.log("School menu updated successfully.");
    } catch (error) {
        console.error("Error fetching menu:", error);
    }
}

updateMenu();
