// Tracks whether the pointer is over a panel (any "dock" window) and reports
// enter/leave transitions to scroll-vol-daemon over D-Bus.

const SERVICE = "local.ScrollVol";
const PATH = "/local/ScrollVol";
const IFACE = "local.ScrollVol";

let docks = [];
let overPanel = false;

function trackWindow(window) {
    if (window.dock && docks.indexOf(window) === -1) {
        docks.push(window);
    }
}

function untrackWindow(window) {
    const i = docks.indexOf(window);
    if (i !== -1) {
        docks.splice(i, 1);
    }
}

function pointerOverDock(pos) {
    for (let i = 0; i < docks.length; ++i) {
        const w = docks[i];
        if (w.hidden || w.minimized) {
            continue;
        }
        const g = w.frameGeometry;
        if (pos.x >= g.x && pos.x < g.x + g.width &&
            pos.y >= g.y && pos.y < g.y + g.height) {
            return true;
        }
    }
    return false;
}

function update() {
    const now = pointerOverDock(workspace.cursorPos);
    if (now !== overPanel) {
        overPanel = now;
        callDBus(SERVICE, PATH, IFACE, "SetOverPanel", now);
    }
}

workspace.windowList().forEach(trackWindow);
workspace.windowAdded.connect(trackWindow);
workspace.windowRemoved.connect(function (window) {
    untrackWindow(window);
    update();
});
workspace.cursorPosChanged.connect(update);
