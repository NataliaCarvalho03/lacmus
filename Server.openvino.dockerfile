FROM openvino/ubuntu18_runtime:latest

RUN mkdir /home/openvino/app && mkdir /home/openvino/app/snapshots
WORKDIR /home/openvino/app
COPY inference_openvino.py /home/openvino/app/inference_openvino.py
COPY snapshots/resnet50_liza_alert_v1_interface.bin /home/openvino/app/snapshots/resnet50_liza_alert_v1_interface.bin
COPY snapshots/resnet50_liza_alert_v1_interface.xml /home/openvino/app/snapshots/resnet50_liza_alert_v1_interface.xml

RUN pip3 install flask pybase64

EXPOSE 5000/tcp
EXPOSE 5000/udp

CMD bash -c "source ${INTEL_OPENVINO_DIR}/bin/setupvars.sh && python3 inference_openvino.py"