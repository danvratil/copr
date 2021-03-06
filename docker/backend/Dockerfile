FROM fedora:23
MAINTAINER clime@redhat.com

COPY files/etc/yum.repos.d/ /etc/yum.repos.d/

RUN dnf -y update
RUN dnf -y install dnf-plugins-core
RUN dnf -y install htop
RUN dnf -y install tito
RUN dnf -y install wget
RUN dnf -y install net-tools
RUN dnf -y install copr-backend
RUN dnf -y install iputils
RUN dnf -y install vim
RUN dnf -y install mlocate
RUN dnf -y install git
RUN dnf -y install sudo
RUN dnf -y install python-nova
RUN dnf -y install openssh-server
RUN dnf -y install supervisor
RUN dnf -y install psmisc

# builder packages
RUN dnf -y install fedpkg-copr
RUN dnf -y install packagedb-cli
RUN dnf -y install fedora-cert
RUN dnf -y install mock
RUN dnf -y install mock-lvm
RUN dnf -y install createrepo
RUN dnf -y install yum-utils
RUN dnf -y install pyliblzma
RUN dnf -y install rsync
RUN dnf -y install openssh-clients
RUN dnf -y install libselinux-python
RUN dnf -y install libsemanage-python
RUN dnf -y install rpm
RUN dnf -y install glib2
RUN dnf -y install ca-certificates
RUN dnf -y install scl-utils-build
RUN dnf -y install ethtool

RUN export LANG=en_US.UTF-8
RUN setcap cap_net_raw,cap_net_admin+p /usr/bin/ping

COPY files/ /

RUN ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -q

RUN echo 'root:passwd' | chpasswd
RUN mkdir /root/.ssh &&  chmod 700 /root /root/.ssh
RUN touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
RUN ssh-keygen -f /root/.ssh/id_rsa -N '' -q -C root@locahost
RUN cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys

#RUN echo 'copr:passwd' | chpasswd
#RUN echo 'copr ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers
#RUN mkdir /home/copr/.ssh && chmod 700 /home/copr /home/copr/.ssh
#RUN ssh-keygen -f /home/copr/.ssh/id_rsa -N '' -q -C copr@locahost
#RUN touch /home/copr/.ssh/authorized_keys && chmod 600 /home/copr/.ssh/authorized_keys
#RUN cat /home/copr/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
#RUN cat /home/copr/.ssh/id_rsa.pub >> /home/copr/.ssh/authorized_keys
#RUN chown copr:copr -R /home/copr
#RUN usermod -a -G mock copr

CMD ["/bin/run.sh"]
