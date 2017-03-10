#!/usr/bin/env python

# all the imports


from flask import Flask, request, session, redirect, url_for, \
    render_template, make_response
import state_manager
from threading import Thread, Event, Timer
import datetime
from enum import Enum

# configuration
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

# simulator state
global events
events = []


def _make_status_response(status):
    response = make_response()
    response.status_code = status
    return response


@app.route('/')
def vehicle_data():
    global gState
    return render_template('vehicle_controls.html', IP=gState.local_ip,
                           accelerator=gState.accelerator_pedal_position,
                           angle=gState.steering_wheel_angle,
                           received_messages=list(reversed(gState.received_messages()))[:25])


@app.route('/stop', methods=['POST'])
def stop():
    # Stop the automatic updates
    session['updates_paused'] = True
    global gState
    gState.pause()
    return redirect(url_for('vehicle_data'))


@app.route('/single', methods=['POST'])
def single():
    # make a global socket
    global gState
    gState.update_once()
    return redirect(url_for('vehicle_data'))


@app.route('/start', methods=['POST'])
def start():
    # make a global socket
    session.pop('updates_paused', None)
    global gState
    gState.resume()
    return redirect(url_for('vehicle_data'))


@app.route('/custom-message', methods=['POST'])
def send_custom_message():
    name = request.form['custom_message_name']
    value = request.form['custom_message_value']
    event = request.form['custom_message_event']

    session['custom_message_name'] = name
    session['custom_message_value'] = value
    session['custom_message_event'] = event
    gState.send_callback(name, value, event)
    return redirect(url_for('vehicle_data'))


@app.route('/_set_data', methods=['POST'])
def set_data():
    global gState

    name = request.form['name']

    if name == "angle":
        gState.steering_wheel_angle = float(request.form['value'])
    elif name == "accelerator":
        gState.accelerator_pedal_position = float(request.form['value'])
    elif name == "brake":
        gState.brake_pedal_position = float(request.form['value'])
    elif name == "parking_brake_status":
        gState.parking_brake_status = python_bool(request.form['value'])
    elif name == "ignition_status":
        gState.ignition_status = request.form['value']
    elif name == "manual_trans_status":
        gState.manual_trans_status = python_bool(request.form['value'])
    elif name == "headlamp_status":
        gState.headlamp_status = python_bool(request.form['value'])
    elif name == "high_beam_status":
        gState.high_beam_status = python_bool(request.form['value'])
    elif name == "windshield_wiper_status":
        gState.windshield_wiper_status = python_bool(request.form['value'])
    elif name == "door_status":
        gState.update_door(request.form['value'], python_bool(
            request.form['event']))
    elif name == "gear_lever_position":
        gState.gear_lever_position = request.form['value']
    elif name == "latitude":
        gState.latitude = float(request.form['value'])
    elif name == "longitude":
        gState.longitude = float(request.form['value'])
    elif name == "upshift":
        gState.upshift()
    elif name == "downshift":
        gState.downshift()
    else:
        print("Unsupported data received from UI: " + str(request.form))

    return _make_status_response(201)


def python_bool(value):
    if value == "true":
        return True
    if value == "false":
        return False
    else:
        return None


@app.route('/_get_data')
def get_data():
    return gState.dynamics_data


class DriveAction():
    def __init__(self, method, comment='', args=[], kwargs={}):
        self.method = method
        self.args = args
        self.kwargs = kwargs


class DriveEvent():
    def __init__(self, action, duration=0, comment=''):
        self.action = action
        self.duration = duration
        self.comment = comment
        self.task = None

    def __str__(self):
        return "Time: {} --- Action: {}".format(datetime.datetime.now(), self.comment)


def print_time(comment=''):
    print "Time: {} --- Action: {}".format(datetime.datetime.now(), comment)


def change_ignition_status(state):
    print "Time: {}".format(datetime.datetime.now())
    print 'turning ignition {}'.format(state)
    if state == IgnitionState.ON:
        gState.ignition_status = 'start'
    else:
        gState.ignition_status = 'stop'


def drive():
    print "Time: {}".format(datetime.datetime.now())
    print 'driving'
    gState.accelerator_pedal_position = 15
    gState.brake_pedal_position = 0


def stop():
    print "Time: {}".format(datetime.datetime.now())
    print "stopping"
    gState.accelerator_pedal_position = 0
    # It's an abrupt stop
    gState.brake_pedal_position = 100


def schedule_event(evt):
    evt.task = Timer(evt.duration, evt.action.method, evt.action.args, evt.action.kwargs)
    # enqueue this event
    events.append(evt)


class IgnitionState(Enum):
    OFF = 0
    ON = 1
    RUNNING = 2
    ACCESSORY = 3


if __name__ == '__main__':
    flask_port = 50000
    print('For the UI, navigate a browser to localhost:' + str(flask_port))

    print('Creating headless state manager')

    global gState
    gState = state_manager.StateManager()

    gState.ignition_status = 'off'


    car_off_action = DriveAction(change_ignition_status, 'ignition off', [IgnitionState.OFF])
    schedule_event(DriveEvent(car_off_action, 0))


    # Don't start immediately such that we can let the UI initialize
    simulation_time = 10
    # Start the car and sit idle for 5 seconds
    start_car_action = DriveAction(change_ignition_status, 'begin trip', [IgnitionState.ON])
    schedule_event(DriveEvent(start_car_action, simulation_time))
    simulation_time += 5

    # Drive for 30 seconds
    drive_action = DriveAction(drive, 'drive')
    schedule_event(DriveEvent(drive_action, simulation_time))
    simulation_time += 30

    # Stop and remain in place for 20+ seconds
    stop_action = DriveAction(stop, 'stopping')
    schedule_event(DriveEvent(stop_action, simulation_time))
    simulation_time += 20

    # Drive again for 30 seconds
    schedule_event(DriveEvent(drive_action, simulation_time))
    simulation_time += 30

    # Stop again
    schedule_event(DriveEvent(stop_action, simulation_time))
    simulation_time += 20

    # Drive again for 30 seconds
    schedule_event(DriveEvent(drive_action, simulation_time))
    simulation_time += 30

    # Stop again
    schedule_event(DriveEvent(stop_action, simulation_time))
    simulation_time += 60

    # Ignition off
    schedule_event(DriveEvent(car_off_action, simulation_time))

    # Schedule all timer tasks
    for evt in events:
        evt.task.start()


    app.run(use_reloader=False, host='0.0.0.0', port=flask_port)
