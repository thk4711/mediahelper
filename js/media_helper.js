var config               = {};
var modes                = [];
var controls             = undefined;
var control_update_delay = 300;
var last_control_update  = 0;
var fold_flag            = true;
var sp_flag              = true;
var need_update          = false;
var last_updated         = millis();
var update_delay         = 100;
var current_values       = {};
var old_values           = {};
var external_update      = false;
var old_metadata         = {artist:"", album:"", track:"", cover:""};

//----------------------------------------------------------------------------//
//                     do some stuff at page load                             //
//----------------------------------------------------------------------------//
$(document).ready(function()
  {
  $.getJSON( "/getconfig", function( data ){
    config = data;
    start_socket();
    });
  $('#prev').on('click', function(){perform_request("/prev");});
  $('#play').on('click', function(){
    perform_request("/play");
    document.getElementById("play").style.display="none";
    $("#pause").fadeIn();});
  $('#pause').on('click', function(){
    perform_request("/pause");
    document.getElementById("pause").style.display="none";
    $("#play").fadeIn(); });

  $('#headphone-on').on('click', function(){
    perform_request("/speaker");
    document.getElementById("headphone-on").style.display="none";
    $("#speaker-on").fadeIn();});
  $('#speaker-on').on('click', function(){
    perform_request("/headphone");
    document.getElementById("speaker-on").style.display="none";
    $("#headphone-on").fadeIn();
  });

  $('#next').on('click', function(){perform_request("/next");});
  add_buttons();
  add_sliders();
  var update_timer = setInterval(check_sliders, 1000);

  $('#myclock').thooClock({
    size:300,                               // size of the clock
    dialColor:'#DDDDDD',                    // foreground-color of dial can be defined as hex, colorstring, or rgb, rgba function
    dialBackgroundColor:'transparent',      // background-color of dial
    secondHandColor:'#F3A829',              // color of second hand
    minuteHandColor:'#AAAAAA',              // color of minute hand
    hourHandColor:'#AAAAAA',                // color of hour hand
    alarmHandColor:'#FFFFFF',               // color of alarm hand (alarm hand only visible if alarmTime is set to 'hh:mm')
    alarmHandTipColor:'#026729',            // color of tip of alarm hand
    hourCorrection:'+0',                    // hour correction e.g. +5 or -3
    alarmCount:1,                           // how many times should the onAlarm Callback function be fired
    //alarmTime:'14:25',                    // alarm time as Date object or String : "hh", "hh:mm", "hh:mm:ss"
    showNumerals:true,                      // show numerals on dial true/false
    brandText:'RASPIDIO',                   // uppercase text on clock dial
    brandText2:'TFT edition',               // lowercase text on clock dial
  });

  });

//----------------------------------------------------------------------------//
//                      togle controls                                        //
//----------------------------------------------------------------------------//
function togle(){
  if (sp_flag == false) {
    $('#sp_other').text('more controls ');
    $("#other_controls").fadeOut();
    sp_flag = true; }
  else {
    $('#sp_other').text('less controls ');
    $("#other_controls").fadeIn();
    sp_flag = false; }
  }

//----------------------------------------------------------------------------//
//                     get buttons                                            //
//----------------------------------------------------------------------------//
function add_buttons(){
  $.getJSON( "/getbuttons", function( data ){
    var button_html = data.html;
    var button_js   = data.js;
    $( "#buttons" ).append( button_html );
    $( "#buttons" ).promise().done(function() {
      $( "body" ).append( button_js );
      });
    });
  $.getJSON( "/getmodes", function( data ){
    modes = data;
    });
}

//----------------------------------------------------------------------------//
//                     add sliders to page                                    //
//----------------------------------------------------------------------------//
function add_sliders(){
  $.getJSON( "/getsliders", function( data ){
    var slider_html = data.html;
    controls   = data.controls;
    $( "#sliders" ).append( slider_html );
    for (var i in controls) {
      current_values[controls[i]['name']] = 0;
      old_values[controls[i]['name']]     = -1;
      var id = "#"+ controls[i]['name'];
      if ( controls[i]['type'] == 'slider') {
        $(id).slider({tooltip: 'hide'});
        var code = "$('" + id + "').on('change', function(event) { change_control( '" + controls[i]['name'] + "' , event.value.newValue) });";
        code += "$('" + id + "').on('slide', function(event) { change_control( '" + controls[i]['name'] + "' , event.value) });";
        eval(code);
        }
      if ( controls[i]['type'] == 'switch') {
        var code = "$('" + id + "').on('change', function(event) { change_control( '" + controls[i]['name'] + "' , $('" + id + "').is(':checked') ) });";
        eval(code);
        }
    }
  });
}

//----------------------------------------------------------------------------//
//                 check sliders for changes                                  //
//----------------------------------------------------------------------------//
function check_sliders(){
  var diff = millis() - last_updated;
  if (need_update  && diff > update_delay) {
    for (var i in controls) {
      if (current_values[controls[i]['name']] != old_values[controls[i]['name']]) {
        transmit_control(controls[i]['name'], current_values[controls[i]['name']]);
        old_values[controls[i]['name']] = current_values[controls[i]['name']];
        }
      }
    need_update = false;
    last_updated = millis();
    }
  }

//----------------------------------------------------------------------------//
//                     perform a get request                                  //
//----------------------------------------------------------------------------//
function perform_request(path) {
  var now = millis();
  $.get(path,{},function(data){}).done(function(data) {
    //updateStatus();
    });
  }

//----------------------------------------------------------------------------//
//                     get milli seconds since 1070                           //
//----------------------------------------------------------------------------//
function millis() {
  var date = new Date()
  var ticks = date.getTime()
  return(ticks) }

//----------------------------------------------------------------------------//
//                     send volume change to mirror                           //
//----------------------------------------------------------------------------//
function change_control(what, new_value) {
  var value = undefined;
  if(typeof(new_value) === "boolean" ) {
    if (new_value == true) {value = 1}
    else  {value = 0}
    }
  else {
    value = new_value;
  }
  current_values[what] = value;
  need_update = true;
  }

//----------------------------------------------------------------------------//
//                     send volume change to mirror                           //
//----------------------------------------------------------------------------//
function transmit_control(what, value) {
  if ( external_update ) {
    external_update = false;
    return;
    }
  if (millis() - last_control_update > control_update_delay) {
      last_control_update = millis();
      old_values.what = value;
      var post_data = { control: what, value: value}
      $.ajax({
        url: '/setcontrols',
        type: 'POST',
        async: 'false',
        data: post_data
        });
      }
  }

//----------------------------------------------------------------------------//
//                     send volume change to mirror                           //
//----------------------------------------------------------------------------//
function switch_mode(new_mode) {
  $.ajax({
    url: '/mode',
    type: 'POST',
    async: 'false',
    data: { mode: new_mode }
    }).done(function(data) {
        highlight_active_icon(new_mode);
        });
  }

//----------------------------------------------------------------------------//
//       get some stats from mirror and update display                        //
//----------------------------------------------------------------------------//
function highlight_active_icon(active_mode)  {
  for (var i in modes) {
    var oid = '#' + modes[i];
    if (modes[i] == active_mode) { $(oid).fadeTo("slow", 1); }
    else { $(oid).fadeTo("slow", 0.3); } }
    $.getJSON( "/controls", function( data )
      {
      if (data.controls) {
        $("#playback-controls").fadeIn();
        $("#metadata").fadeIn(); }
      else {
        document.getElementById("playback-controls").style.display="none";
        document.getElementById("metadata").style.display="none";
      }
    })
  }

//----------------------------------------------------------------------------//
//       update elements                                                      //
//----------------------------------------------------------------------------//
function updateElements(data) {
  if ('play_mode' in data){
    if (data.play_mode == true){
      document.getElementById("play").style.display="none";
      $("#pause").fadeIn(); }
    else {
      document.getElementById("pause").style.display="none";
      $("#play").fadeIn(); } }
  if ('desired_mode' in data) {
    highlight_active_icon(data.desired_mode) }
  if ('volume' in data){
    $("#volume").slider('setValue', parseInt(data.volume), true); }
  if ('bass' in data){
    $("#bass").slider('setValue', parseInt(data.bass), true); }
  if ('treble' in data){
    $("#treble").slider('setValue', parseInt(data.treble), true); }
  if ('loudness' in data){
    if (parseInt(data.loudness) == 0){
      $("#loudness").prop( 'checked', false );}
    else  {
      $("#loudness").prop( 'checked', true );} }
  if ('cover' in data){
    if ( old_metadata.cover != data.cover ){
      console.log("cover: " + data.cover);
      old_metadata.cover = data.cover;
      if ( data.cover == '/images/pause.png' || data.cover == '/images/black.png'){
        console.log("pausing");
        $("#coverdiv").fadeOut("slow", function () {
          $("#myclock").fadeIn("slow");});
        }
      else {
        $("#myclock").fadeOut("fast", function () {
          $("#coverdiv").fadeOut("slow", function () {
            $("#albumCover").attr("src",data.cover);
            setTimeout(function() {
              $("#coverdiv").fadeIn("slow");
            }, 1000); }); }); }
      }
    }
  if ('track' in data){
    if ( old_metadata.track != data.track ){
    old_metadata.track = data.track
    $("#track").fadeOut("slow", function () {
      $('#track span').text(data.track);
      $("#track").fadeIn("slow");
    }); } }
  if ('artist' in data) {
    if ( old_metadata.artist != data.artist ){
    old_metadata.artist = data.artist
    $("#artist").fadeOut("slow", function () {
      $('#artist span').text(data.artist);
      $("#artist").fadeIn("slow");
    }); } }
  if ('album' in data) {
    if ( old_metadata.album != data.album ){
    old_metadata.album = data.album
    $("#album").fadeOut("slow", function () {
      $('#album span').text(data.album);
      $("#album").fadeIn("slow");
    }); } }
}

//----------------------------------------------------------------------------//
//                     start websocket communication                          //
//----------------------------------------------------------------------------//
function start_socket(){
  var ws_url = config.ws_base + config.ws_port;
  var socket = new WebSocket(ws_url);
  socket.onmessage = function (event) {
    var obj = JSON.parse(event.data);
    var text = '';
    external_update = true;
    updateElements(obj);
    };
    socket.onopen=function(event){
      $.getJSON( "/statusinfo", function( data ) {
        updateElements(data);
        });
      if(window.timerID){
        window.clearInterval(window.timerID);
        window.timerID=0;
      }
    }
    socket.onclose=function(event){
      if(!window.timerID){
        window.timerID=setInterval(function(){start_socket()}, 5000);
      }
    }
  }
