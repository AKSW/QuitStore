/*
 *  jQuery Commits Graph - v0.1.4
 *  A jQuery plugin to display git commits graph using HTML5/Canvas.
 *  https://github.com/tclh123/commits-graph
 *
 *  Copyright (c) 2014
 *  MIT License
 */
function Route(a, b, c) {
    var d = this;
    d._data = b, d.commit = a, d.options = c, d.from = b[0], d.to = b[1], d.branch = b[2]
}

function Commit(a, b, c, d) {
    var e = this;
    e._data = c, e.graph = a, e.idx = b, e.options = d, e.sha = c[0], e.dot = c[1], e.dot_offset = e.dot[0], e.dot_branch = e.dot[0], e.routes = $.map(c[2], function(a) {
        return new Route(e, a, d)
    })
}

function backingScale() {
    return "devicePixelRatio" in window && window.devicePixelRatio > 1 ? window.devicePixelRatio : 1
}

function GraphCanvas(a, b) {
    var c = this;
    c.data = a, c.options = b, c.canvas = document.createElement("canvas"), c.canvas.style.height = b.height + "px", c.canvas.style.width = b.width + "px", c.canvas.height = b.height, c.canvas.width = b.width;
    var d = backingScale();
    "horizontal" === c.options.orientation ? 1 > d && (c.canvas.width = c.canvas.width * d, c.canvas.height = c.canvas.height * d) : d > 1 && (c.canvas.width = c.canvas.width * d, c.canvas.height = c.canvas.height * d), c.options.scaleFactor = d, c.colors = ["#e11d21", "#fbca04", "#009800", "#006b75", "#207de5", "#0052cc", "#5319e7", "#f7c6c7", "#fad8c7", "#fef2c0", "#bfe5bf", "#c7def8", "#bfdadc", "#bfd4f2", "#d4c5f9", "#cccccc", "#84b6eb", "#e6e6e6", "#ffffff", "#cc317c"]
}

function Graph(a, b) {
    var c = this,
        d = {
            height: 800,
            width: 200,
            y_step: 20,
            x_step: 20,
            orientation: "vertical",
            dotRadius: 3,
            lineWidth: 2
        };
    c.element = a, c.$container = $(a), c.data = c.$container.data("graph");
    var e = $.extend({}, d, b).x_step,
        f = $.extend({}, d, b).y_step;
    "horizontal" === b.orientation ? (d.width = (c.data.length + 2) * e, d.height = (branchCount(c.data) + .5) * f) : (d.width = (branchCount(c.data) + .5) * e, d.height = (c.data.length + 2) * f), c.options = $.extend({}, d, b), c._defaults = d, c.applyTemplate()
}
Route.prototype.drawRoute = function(a) {
        var b = this;
        if ("horizontal" === b.options.orientation) {
            var c = b.options.width * b.options.scaleFactor - (b.commit.idx + .5) * b.options.x_step * b.options.scaleFactor,
                d = (b.from + 1) * b.options.y_step * b.options.scaleFactor,
                e = b.options.width * b.options.scaleFactor - (b.commit.idx + .5 + 1) * b.options.x_step * b.options.scaleFactor,
                f = (b.to + 1) * b.options.y_step * b.options.scaleFactor;
            a.strokeStyle = b.commit.graph.get_color(b.branch), a.beginPath(), a.moveTo(c, d), d === f ? a.lineTo(e, f) : d > f ? a.bezierCurveTo(c - b.options.x_step * b.options.scaleFactor / 3 * 2, d + b.options.y_step * b.options.scaleFactor / 4, e + b.options.x_step * b.options.scaleFactor / 3 * 2, f - b.options.y_step * b.options.scaleFactor / 4, e, f) : f > d && a.bezierCurveTo(c - b.options.x_step * b.options.scaleFactor / 3 * 2, d - b.options.y_step * b.options.scaleFactor / 4, e + b.options.x_step * b.options.scaleFactor / 3 * 2, f + b.options.y_step * b.options.scaleFactor / 4, e, f)
        } else {
            var g = (b.from + 1) * b.options.x_step * b.options.scaleFactor,
                h = (b.commit.idx + .5) * b.options.y_step * b.options.scaleFactor,
                i = (b.to + 1) * b.options.x_step * b.options.scaleFactor,
                j = (b.commit.idx + .5 + 1) * b.options.y_step * b.options.scaleFactor;
            a.strokeStyle = b.commit.graph.get_color(b.branch), a.beginPath(), a.moveTo(g, h), g === i ? a.lineTo(i, j) : a.bezierCurveTo(g - b.options.x_step * b.options.scaleFactor / 4, h + b.options.y_step * b.options.scaleFactor / 3 * 2, i + b.options.x_step * b.options.scaleFactor / 4, j - b.options.y_step * b.options.scaleFactor / 3 * 2, i, j)
        }
        a.stroke()
    }, Commit.prototype.drawDot = function(a) {
        var b = this,
            c = b.options.dotRadius;
        if ("horizontal" === b.options.orientation) {
            var d = b.options.width * b.options.scaleFactor - (b.idx + .5) * b.options.x_step * b.options.scaleFactor,
                e = (b.dot_offset + 1) * b.options.y_step * b.options.scaleFactor;
            a.fillStyle = b.graph.get_color(b.dot_branch), a.beginPath(), a.arc(d, e, c * b.options.scaleFactor, 0, 2 * Math.PI, !0)
        } else {
            var f = (b.dot_offset + 1) * b.options.x_step * b.options.scaleFactor,
                g = (b.idx + .5) * b.options.y_step * b.options.scaleFactor;
            a.fillStyle = b.graph.get_color(b.dot_branch), a.beginPath(), a.arc(f, g, c * b.options.scaleFactor, 0, 2 * Math.PI, !0)
        }
        a.fill()
    }, GraphCanvas.prototype.toHTML = function() {
        var a = this;
        return a.draw(), $(a.canvas)
    }, GraphCanvas.prototype.get_color = function(a) {
        var b = this,
            c = b.colors.length;
        return b.colors[a % c]
    }, GraphCanvas.prototype.draw = function() {
        var a = this,
            b = a.canvas.getContext("2d");
        b.lineWidth = a.options.lineWidth, console.log(a.data);
        for (var c = a.data.length, d = 0; c > d; d++) {
            var e = new Commit(a, d, a.data[d], a.options);            
            for (var f = 0; f < e.routes.length; f++) {
                var g = e.routes[f];
                g.drawRoute(b)
            }
            e.drawDot(b);
        }
    }, branchCount = function(a) {
        for (var b = -1, c = 0; c < a.length; c++)
            for (var d = 0; d < a[c][2].length; d++)(b < a[c][2][d][0] || b < a[c][2][d][1]) && (b = Math.max.apply(Math, [a[c][2][d][0], a[c][2][d][1]]));
        return b + 1
    }, Graph.prototype.applyTemplate = function() {
        var a = this,
            b = new GraphCanvas(a.data, a.options),
            c = b.toHTML();
        c.appendTo(a.$container)
    },
    function(a) {
        a.fn.commits = function(b) {
            return this.each(function() {
                a(this).data("plugin_commits_graph") || a(this).data("plugin_commits_graph", new Graph(this, b))
            })
        }
    }(window.jQuery, window);