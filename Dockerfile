FROM python:3.10
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY pip.conf /root/.pip/pip.conf
COPY requirements.txt /usr/src/app/
EXPOSE 9000
EXPOSE 1833
RUN pip install -r /usr/src/app/requirements.txt
RUN rm -rf /usr/src/app
COPY . /usr/src/app
CMD [ "python", "manage.py", "runserver", "0.0.0.0:9000", "--noreload"]