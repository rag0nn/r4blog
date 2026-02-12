### R4BLOG Blog Website Uygulaması

[Github Reposu](https://github.com/rag0nn/r4blog)

Tamamen kişisel kullanım için açık kaynaklı olarak geliştirilen bir projedir.
Dilendiği gibi kullanılabilir, çoğaltılabilir. 

Mevcut olarak not vb. fikri işler için 'post', geliştirilen proje tanıtımları için 'project' adlı url ve sınıf gruplarıyla kullanılır. Bunların dışında bir de about kısmını bulundurur.

Sistem sadece hash'lenmiş bir adet şifre ile çalışır. Ekleme, silme güncelleme için kullanılır. Şifre oluşturmak için aşağıya bakınız.

#### Kullanılan Diller Ve Frame'ler**
- Flask (Python)
- HTML
- CSS
- JS

#### Gereklilikler

Gerekli paketle requirements.txt dosyasında güncel olarak tutulmaktadır. 

! Bcrypt'in eski versiyonu olan python-bcrypt'in kullanılmadığına dikkat edilmelidir.

! Proje Python 3.9.21 ile denenmiştir

#### Kullanım

Gereklilikler kurulduğundan sonra bir '.env' dosyası oluşturulmalı ve HASHED_PSW = <__Oluşturulan Şifre__> olarak bir değişken oluşturulmalıdır. 

**Şifre Oluşturma**
create_password.py dosyası kullanılarak yeni bir hashlenmiş şifre oluşturabilir ve .env dosyasına bu şifreyi yazabilirsiniz.