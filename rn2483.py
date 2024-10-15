#!/usr/bin/env python3
# coding: utf-8

# #############################################################################
#
# Import zone
#
import time
import logging
import serial

# #############################################################################
#
# Configuration
#

# LoRa parameters. JOINEUI is sometimes called APPEUI
APPKEY   = "0123456789ABCDEF0123456789ABCDEF"
JOINEUI   = "DEAD25DEAD25DEAD"
DEVEUI   = "DEADDEAD00090002"

#Port, on windows it's COM something
PORT     = '/dev/ttyACM0'
BAUDRATE = 57600

MESSAGE  = f"Hello from {DEVEUI}"

SPREADING_FACTOR = 7

# In python you can use a logger for debug messages visibility
# Here I set my logging message format
logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s,%(msecs)03d %(levelname)-8s - [%(filename)s.%(funcName)-10s:\
%(lineno)-3d.] - %(message)s')


# #############################################################################
#
# Available commands for RN2483 Module
#
# sys <sleep|reset|factoryRESET>
# mac get <deveui|appeui|devaddr|txport|txmode|poweridx|dr|adr|band|retx|rx1|rx2|ar|rx2dr|rx2freq>
# mac set <deveui|appeui|appkey|devaddr|appskey|nwkskey|txport|txmode|pwridx|dr|adr|bat|retx|linkchk
#          |rx1|ar|rx2dr|rx2freq|sleep_duration> <value>
# mac save
# mac join <otaa|abp>
# mac tx <payload>
#
# Note : mac send LoRaWAN packets, radio send LoRa data 


# #############################################################################
#
# Functions
#

def setup_serial(port:str=PORT,baudrate:int=BAUDRATE,bytesize:int=serial.EIGHTBITS,
                        parity:str=serial.PARITY_NONE,stopbits:int=serial.STOPBITS_ONE,
                        dtr:int=False):
    """
    Function to setup my serial connection
    Params:
        port:str        : Port used for my connection, default value PORT
        baudrate:int    : Baudrate, default value BAUDRATE
        bytesize:int    : bytesize, default value serial.EIGHTBITS
        parity:str      : Bit parity, default value serial.PARITY_NONE
        stopbits:int    : Stop bits, default value serial.STOPBITS_ONE
        dtr:bool        : Data Terminal Ready, default value False
    Returns :
        sp:Serial.Serial: A serial connection
    """
    try:
        sp = serial.Serial()
        sp.port = port
        sp.baudrate = baudrate
        sp.bytesize = bytesize
        sp.parity = parity
        sp.stopbits = stopbits
        sp.dtr=dtr
        sp.open()
        return sp
    except (ValueError,serial.SerialException) as exception:
        logging.critical("Could not open the serial connection.")
        raise exception

def send(sp:serial.Serial,data:str):
    """
    Send data through the serial connection
        Param:
            sp:serial.Serial : serial.Serial object used for the RN2485
            data:str : Data to encode and send
        Returns :
            decoded_response:str: Returns a response if got one
    """
    #Encode data and send it through the serial connection
    data_to_send = (data.rstrip()+"\x0d\x0a").encode()
    sp.write(data_to_send)
    time.sleep(0.2)

    #Wait for a response
    rdata=sp.readline()
    while not rdata:
        rdata = sp.readline()

    #Decode response and send it
    decoded_response = rdata.strip().decode()
    logging.debug("Decoded response : %s",decoded_response)
    return decoded_response

def lora_setup(sp:serial.Serial,spreading_factor:int):
    """
    Function to setup my LoRa parameters for my device
    No error raised if invalid_parameter, be careful
    Duty cycle set to 1.0 for experimentation purposes ! 
    DO NOT DEPLOY WITH DUTY CYCLE SET TO 1.00
    Params : 
        spreading_factor:int : 7 to 12, used to set up the data rate
            dr config bit/s
            0 LoRa: SF12 / 125 kHz 250
            1 LoRa: SF11 / 125 kHz 440
            2 LoRa: SF10 / 125 kHz 980
            3 LoRa: SF9 / 125 kHz 1760
            4 LoRa: SF8 / 125 kHz 3125
            5 LoRa: SF7 / 125 kHz 5470
        adr:bool : Using adr or not True : yes, False : no
    Returns :
        bool: True if joined, False if not
    """
    #data rate : https://www.lab5e.com/docs/lora/dr_sf/
    # dr config bit/s
    # 0 LoRa: SF12 / 125 kHz 250
    # 1 LoRa: SF11 / 125 kHz 440
    # 2 LoRa: SF10 / 125 kHz 980
    # 3 LoRa: SF9 / 125 kHz 1760
    # 4 LoRa: SF8 / 125 kHz 3125
    # 5 LoRa: SF7 / 125 kHz 5470
    data_rate = abs(spreading_factor-12)


    # Setting the same parameters again after a sys reset is useless, because sys
    #     reset just reload the parameters in the EEPROM (the ones you just set the round before)
    # If you want to do a factory reset because something is not working as intended
    # Replace with sys factoryRESET
    logging.info("Resetting device")
    response = send(sp,"sys reset")
    logging.info("Reset response : %s",response)

    logging.info("Setting APPKEY : %s",APPKEY)
    response = send(sp,f"mac set appkey {APPKEY}")
    logging.info("Set APPKEY response : %s",response)

    logging.info("Setting JOINEUI : %s",JOINEUI)
    response = send(sp,f"mac set appeui {JOINEUI}")
    logging.info("Set JOINEUI response : %s",response)

    logging.info("Setting DEVEUI : %s",DEVEUI)
    response = send(sp,f"mac set deveui {DEVEUI}")
    logging.info("Set DEVEUI response : %s",response)

    logging.info("Setting the data-rate : %s, it's |SPREADING_FACTOR-12|",data_rate)
    response = send(sp,f"mac set dr {data_rate}")
    logging.info("Set data-rate : %s",response)

    #Here, we set the duty cycle to 1.00 for EXPERIMENTATIONS PURPOSES
    # The RN2483 returns no_free_ch when you're not respecting
    # the default duty cycle of 0.33
    # If you deploy something, please, change the duty cycle to
    # an appropried 10%, 1% or 0.1%
    # Bandwith of the 3 channels : 
    # Channel 0 : 868.1
    # Channel 1 : 868.3
    # Channel 2 : 868.5
    for channel in range(0,3):
        #Change duty cycle
        logging.info("Setting channel %s duty cycle to  1.00",channel)
        response = send(sp,f"mac set ch dcycle {channel} 1")
        logging.info("Set %s to dcycle response : %s",channel,response)
        #Channel status to on
        logging.info("Setting channel %s to on",channel)
        response = send(sp,f"mac set ch status {channel} on")
        logging.info("Set %s on response : %s",channel,response)

    logging.info("Saving MAC Settings")
    response = send(sp,"mac save")
    logging.info("Saving mac settings response : %s",response)

    joining=False
    while not joining:
        logging.info("Preparing to join the network")
        response = send(sp,"mac join otaa")
        logging.info("Mac join otaa response : %s",response)
        if "ok" in response:
            joining=True
        time.sleep(2)

    logging.info("Wating to get the accepted response")
    time.sleep(2) #Wait for accepted response
    ret = sp.readline()
    while not ret:
        ret = sp.readline()
    response = ret.strip().decode()
    logging.info("Status of the join request : %s",response)
    if response != "accepted":
        return False
    return True



# #############################################################################
#
# Main
#

def main():
    """
    Main function of the program
    """
    #Make serial connection
    try:
        sp = setup_serial()
    except (ValueError,serial.SerialException) as err:
        logging.error("Failed to create the serial connection, %s:%s",err.__class__,err)
        return 1

    #Message to send
    encoded_message = MESSAGE.encode("utf-8").hex()

    #Command used, cnf for confirmed uncnf for unconfirmed
    command = f"mac tx cnf 220 {encoded_message}"

    #Main loop
    try:
        while True :
            #Setup LoRa
            while not lora_setup(sp,SPREADING_FACTOR):
                logging.error("Failed to connect, retrying in 3s")
                time.sleep(3)
            logging.info("Connected to LoRa network")

            #Loop to send data
            #If I get more than 5 errors, I reset the LoRa parameters'
            error_counts = 0
            while error_counts <= 5:

                #Wait some time to not overload
                logging.info("Waiting to send message")
                time.sleep(10)

                logging.info("Sending command \"%s\"",command)
                if not "ok" in send(sp,command):
                    error_counts+=1
                    logging.error("Could not send the command, retrying")
                    continue
                logging.debug("Message successfuly sent through serial")

                #Try to get response
                #Since I send cnf messages, I want my message to be confirmed
                #If I get a max_rx in the response, Chirpstack is sending me a downlink with data I have to decode
                tries = 0
                ret = sp.readline()
                while not ret and tries <5:
                    time.sleep(1)
                    ret = sp.readline()
                    tries+=1
                if not ret:
                    error_counts+=1
                    logging.error("No response, maybe collision or message lost")
                    continue
                decoded_response = ret.strip().decode()
                logging.info("Got response %s",decoded_response)
                if not "mac_rx" in decoded_response:
                    logging.info("No mac_rx in response, continuing")
                    continue
                logging.info("Got a max_rx (downlink, processing)")
                payload = decoded_response.split(" ")[-1]
                logging.debug("Payload : %s",payload)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt, ending program")
        sp.close()
        return 0


if __name__ == "__main__":
    logging.info("Starting program RN2483")
    main()
