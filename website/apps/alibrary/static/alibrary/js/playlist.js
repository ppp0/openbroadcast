/*
 * PLAYLIST SCRIPTS
 */

/* core */

PlaylistUi = function() {

	var self = this;

	this.interval = false;
	this.interval_loops = 0;
	this.interval_duration = 10000;
	// this.interval_duration = false;
	this.api_url = false;
	
	this.inline_dom_id = 'inline_playlist_holder';
	this.inline_dom_element;
	
	this.current_data;
	this.current_items = new Array;

	this.init = function() {
		
		console.log('PlaylistUi: init');
		console.log(self.api_url);
		
		this.inline_dom_element = $('#' + this.inline_dom_id);

		self.iface();
		self.bindings();

		// set interval and run once
		if(self.interval_duration) {
			self.set_interval(self.run_interval, self.interval_duration);
		}
		self.run_interval();
		
	};

	this.iface = function() {
		// this.floating_inline('lookup_providers', 120)
	};

	this.bindings = function() {


		//self.inline_dom_element.hide(20000)
		var container = $('#inline_playlist_container');

		// states - open / close
		// main box
		$('.ui-persistent > .header', container).live('click', function(e) {
			e.preventDefault();
			var parent = $(this).parents('.ui-persistent');
			if (!parent.hasClass('expanded')) {
				parent.data('uistate', 'expanded');
			} else {
				parent.data('uistate', 'hidden');
			}
		});
		// sub boxes
		
		
		// settings panel / create
		$('.ui-persistent > .form form.create', container).live('submit', function(e) {
			e.preventDefault();
			var name = $('input.name', $(this)).val();
			self.create_playlist(name);
		});
		
		// actions
		$('.playlist_holder > .header a', container).live('click', function(e) {
			e.preventDefault();
			
			var id = $(this).parents('.playlist_holder').data('object_id');
			var action = $(this).data('action');
			
			$.log(action, id);
			
			if(action == 'delete' && confirm('Sure?')) {
				self.delete_playlist(id);
			}
			
			//var name = $('input.name', $(this)).val();
			//self.create_playlist(name);
		});
		
		
		// Playlist as a whole, edit name
		$('div.playlist_holder .header .action.edit').live('click', function() {
			var edit = $('div.edit', $(this).parent().parent().parent());
			if(edit.css("display") == "none") {
				edit.show();
			} else {
				edit.hide();
			}
			return false;
		});
		
		// Action on name change & Enter
		$('div.playlist_holder .panel .edit input').live('keypress', function (e) {
	
			if(e.keyCode == 13 || e.keyCode == 9) {
				e.preventDefault();
				
				var id = $(this).attr('id').split("_").pop();;
				var name = $(this).val();

				// Request data
				var data = {
					name : name
				};
	
				$.ajax({
					url: self.api_url + id + '/',
					type: 'PUT',
					data: JSON.stringify(data),
					dataType: "json",
					contentType: "application/json",
					processData:  false,
					success: function(data) {
						//$('#playlist_holder_' + id).hide(500);
						self.run_interval();
					},
					async: true
				});
				
			}
			
		});
		

		
		// list items
		$('.action.download > a', self.inline_dom_element).live('click', function(e){
			e.preventDefault();
		});

		// selector
		
		$('#playlists_inline_selector').live('change', function(e){
			e.preventDefault();
			
			var resource_uri = $(this).val();

			$('.playlist_holder', self.inline_dom_element).hide();

			$.ajax({
				url: resource_uri + 'set-current/',
				type: 'GET',
				dataType: "json",
				contentType: "application/json",
				processData:  false,
				success: function(data) {
					self.run_interval();
				},
				async: false
			});
			
		});
		
		

	};

	// interval
	this.set_interval = function(method, duration) {
		self.interval = setInterval(method, duration);
	};
	this.clear_interval = function(method) {
		self.interval = clearInterval(method);
	};

	this.run_interval = function() {
		self.interval_loops += 1;

		// Put functions needed in interval here
		self.update_playlists();

	};
	
	
	this.create_playlist = function(name) {
		
		var data = {
			'name': name
		};
		
		// alert('create: ' + name);
		
		$.ajax({
			url: self.api_url,
			type: 'POST',
			data: JSON.stringify(data),
			dataType: "json",
			contentType: "application/json",
			processData:  false,
			success: function(data) {
				// self.run_interval();
			},
			async: false
		});
		
		// console.log('data:', data);
		
		self.run_interval();
	};
	
	
	this.delete_playlist = function(id) {

		$.ajax({
			url: self.api_url + id + '/',
			type: 'DELETE',
			dataType: "json",
			contentType: "application/json",
			processData:  false,
			success: function(data) {
				//$('#playlist_holder_' + id).hide(500);
				
				$('#playlist_holder_' + id).fadeOut(160, function() { $(this).remove(); })
				
				
				// self.run_interval();
			},
			async: true
		});
	};
	
	this.update_playlists = function() {
		$.getJSON(self.api_url, function(data) {
			self.update_playlists_callback(data);
		});
	};
	
	this.update_playlists_callback = function(data) {

		self.update_playlist_display(data);
		self.update_playlist_selector(data);
		
		this.current_data = data;
	};
	
	this.update_playlist_display = function(data) {

		// console.log(data)

		var status_map = new Array;
		status_map[0] = 'init';
		status_map[1] = 'done';
		status_map[2] = 'ready';
		status_map[3] = 'progress';
		status_map[4] = 'downloaded';
		status_map[99] = 'error';

		for (var i in data.objects) {

			var item = data.objects[i];
			var target_element = $('#playlist_holder_' + item.id);

			item.status_key = status_map[item.status];
			
			console.log(item);

			// filter out current playlist
			if (item.is_current) {

				if (item.id in self.current_items) {
					self.current_items[item.id] = item;
					console.log('item already present');

					if(item.updated != target_element.attr('data-updated')) {
						console.log('update detected');
						
						var html = ich.tpl_playlists_inline({object: item});
						
						html.attr('data-updated', item.updated);
						target_element.replaceWith(html);
					}
					
				} else {

					var html = ich.tpl_playlists_inline({object: item});
					html.attr('data-last_status', item.status);
					self.inline_dom_element.append(html);

					self.current_items[item.id] = item;
				}
			} else {
				// remove item if not the current one
				target_element.hide(200)
			}
		}
	};
	
	this.update_playlist_selector = function(data) {
		
		// console.log(this.current_data, data)

		if(data.objects.length > 1) {
		
			if( ! Object.equals(this.current_data, data)) {
				console.log('data changed');
	
				var html = ich.tpl_playlists_inline_selector(data);
				$('.playlist-selector', self.inline_dom_element.parent()).html(html);
	
			} else {
				console.log('data unchanged');
			}
		
		}
	};


};















Object.equals = function( x, y ) {
  if ( x === y ) return true;
    // if both x and y are null or undefined and exactly the same

  if ( ! ( x instanceof Object ) || ! ( y instanceof Object ) ) return false;
    // if they are not strictly equal, they both need to be Objects

  if ( x.constructor !== y.constructor ) return false;
    // they must have the exact same prototype chain, the closest we can do is
    // test there constructor.

  for ( var p in x ) {
    if ( ! x.hasOwnProperty( p ) ) continue;
      // other properties were tested using x.constructor === y.constructor

    if ( ! y.hasOwnProperty( p ) ) return false;
      // allows to compare x[ p ] and y[ p ] when set to undefined

    if ( x[ p ] === y[ p ] ) continue;
      // if they have the same strict value or identity then they are equal

    if ( typeof( x[ p ] ) !== "object" ) return false;
      // Numbers, Strings, Functions, Booleans must be strictly equal

    if ( ! Object.equals( x[ p ],  y[ p ] ) ) return false;
      // Objects and Arrays must be tested recursively
  }

  for ( p in y ) {
    if ( y.hasOwnProperty( p ) && ! x.hasOwnProperty( p ) ) return false;
      // allows x[ p ] to be set to undefined
  }
  return true;
}