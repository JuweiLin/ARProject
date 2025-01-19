async function sendCommand() {
    const device = document.getElementById("device").value;
    const command = document.getElementById("command").value;

    const response = await fetch("/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: device, command: command }),
    });

    const result = await response.json();
    alert(result.message);
}
