
const colors = ["blue", "red", "green", "yellow", "black", "purple", "pink", "grey"];

var http_req = function(url, opt) {
	const request = new Request(url, opt);
	return fetch(request)
		.then(response => {
			if (response.status === 200){
				return response.json();
			}
			else
				throw new Error(response);
		});
};

class Application extends EventTarget {
	constructor(){
		super();
		this._config = null;
	}

	get config(){
		return this._config;
	}
	triggerEvent(eventname, arg) {
		let event = new CustomEvent(eventname, {detail: arg});
		app.dispatchEvent(event);
	}
	wsconnect() {
		var url = this._config.ws.url;
		this._webSocket = new WebSocket(url);
		this._webSocket.onopen = function(event){
			console.log("WS Connected");
		}
		this._webSocket.onmessage = function(event){
			console.log("WS Connected");
		}
	}
	startlogtracker(){
		console.log("start logtracking...");
		this.wsconnect();
	}

	onready(){
		var self = this;
		Promise.all([http_req("/ws"), http_req("/files")])
		.then(values => {
			var client_config = {}; 
			client_config.ws = values[0];
			client_config.files = values[1];
			self.triggerEvent("config", client_config);
		})
		.catch(err => { console.error(err); });
	}

	onconfig(event){
		console.log("config loaded", event.detail);
		this._config = event.detail;

		var done_colors = [];

		for (let i in this._config.files){
			var f = this._config.files[i];
			if (f.color == 'auto'){

				var available = colors.filter(col => done_colors.indexOf(col)==-1);
				if (available.length > 0){
					f.color = available[0];			
					done_colors.push(f.color);
				}
			}
			else
			{
				done_colors.push(f.color);			
			}
		}
		this.triggerEvent("start",null);
	}
}

var app = new Application();

app.addEventListener("config", app.onconfig);
app.addEventListener("start", app.startlogtracker);

$(document).ready(() => app.onready());