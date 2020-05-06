from cassandra.cluster import Cluster
from sys import stdin

cont_ID_user = 0
cont_ID_carrito = 0
cont_ID_compras = 0

"""
estados carrito. 1: activo, 2: comprado, 3: inactivo
"""

def create_user():
    global cont_ID_user, session, cluster
    print("Bienvenido a compras en linea!")
    flag = True
    while flag:
        print("Para registrarse porfavor ingrese su email:")
        email = stdin.readline().strip()
        print("Ingrese un nombre de usuario porfavor:")
        flag2 = True
        while flag2:
            username = stdin.readline().strip()
            rows = session.execute("select nombre from usuario where nombre='{0}' allow filtering".format(username))
            if rows:
                print("El nombre de usuario ya esta en uso. Ingrese otro:")
            else:
                flag2 = False
        print("Ingrese su contrasena porfavor:")
        password = stdin.readline().strip()
        cont_ID_user += 1
        id = cont_ID_user
        session.execute(
            """
            INSERT INTO usuario (idU, nombre, correo, contrasena)
            VALUES (%s, %s, %s, %s)
            """,
            (id, username, email, password)
        )
        print("Desea registar otra persona? (Si: 1, No: 0)")
        ans = int(stdin.readline().strip())
        if ans == 0:
            flag = False
    login()

def login():
    global session, cluster
    flag = True
    while flag:
        print("Escriba su nombre de usuario para iniciar sesion o presione 0 para salir")
        username = stdin.readline().strip()
        if username == '0':
            break
        print("Escriba su contrasena:")
        password = stdin.readline().strip()
        rows = session.execute("select nombre, contrasena from usuario where nombre='{0}' and contrasena='{1}' allow filtering".format(username, password))
        if not rows:
            print("Usuario o contrasena incorrecta")
        else:
            print("Has iniciado sesion correctamente")
            interface(rows[0].nombre)

def interface(name):
    global session, cluster, cont_ID_carrito, cont_ID_compras
    print("====================================================================")
    print("Bienvenido {0} ahora podras empezar tus compras en linea".format(name))
    print("====================================================================")
    print("Estos son los productos que tenemos disponible:")
    rows = session.execute('SELECT * FROM producto')
    for row in rows:
        print("id:{5}, {0}, {1}, {2} $, {3} kg, {4}".format(row.nombre, row.descripcion, str(row.precio), str(row.peso), row.tamano, row.idp))
    print("Presione 1 si desea empezar a comprar o 0 para salir")
    flag = True
    shop = int(stdin.readline().strip())
    while flag:
        if shop == 1:
            #creamos un carrito
            rows = session.execute("select idU from usuario where nombre='{0}' allow filtering".format(name))
            id_active_user = rows[0].idu
            cont_ID_carrito += 1
            id_carrito = cont_ID_carrito
            session.execute(
                """
                INSERT INTO carrito (idC, estado, cliente, valorfinal)
                VALUES (%s, %s, %s, %s)
                """,
                (id_carrito, 1, id_active_user, 0)
            )
            print("Si desea descartar por completo la compra, escriba 'descartar'")
            print("Si desea terminar su compra para pagar, escriba 'terminar'")
            print("Para agregar un producto al carrito escriba 'agregar' seguido del id del producto y de la cantidad a comprar")
            print("Para quitar un producto del carrito escriba 'quitar' seguido del id del producto y de la cantidad a quitar")
            ans = stdin.readline().strip()
            while True:
                x = ans.split()
                if x[0] == 'agregar':
                    cont_ID_compras += 1
                    p = int(x[1])
                    cant = int(x[2])
                    #creo la compra (si ya existe una compra de ese producto actualizo la cantidad, si no existe creo la compra)
                    rows = session.execute(
                        "select ids, cantidad from compra where prod={0} and nro_carrito={1} allow filtering".format(p, id_carrito)
                    )
                    if rows:
                        cant_aux = rows[0].cantidad
                        ids_aux = rows[0].ids
                        session.execute(
                            "update compra set cantidad={0} where idS={1} and nro_carrito={2}".format(cant_aux+cant, ids_aux, id_carrito)
                        )
                    else:
                        session.execute(
                            """
                            INSERT INTO compra (idS, nro_carrito, prod, cantidad)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (cont_ID_compras, id_carrito, p, cant)
                        )

                    #encuentro el valor final temporal que lleva el carrito
                    rows = session.execute(
                        "select valorfinal from carrito where idc={0} allow filtering".format(id_carrito)
                    )
                    aux = rows[0].valorfinal

                    #encuentro el precio del producto p
                    rows = session.execute(
                        "select precio from producto where idP={0} allow filtering".format(p)
                    )
                    vp = rows[0].precio

                    #Actualizo el valor final temporal del carrito con lo que tenia + precio del producto
                    session.execute(
                        "update carrito set valorfinal={0} where idC={1}".format(aux+(vp*cant), id_carrito)
                    )

                elif x[0] == 'quitar':
                    p = int(x[1])
                    cant = int(x[2])
                    #actualizo la cantidad del producto en compra
                    rows = session.execute(
                        "select ids, cantidad from compra where prod={0} and nro_carrito={1} allow filtering".format(p, id_carrito)
                    )
                    if not rows:
                        print("El producto a quitar no se encuentra en tu carrito")
                    else:
                        cant_aux = rows[0].cantidad
                        ids_aux = rows[0].ids
                        if cant > cant_aux:
                            print("Estas quitando mas productos de los que tienes en tu carrito")
                        else:
                            session.execute(
                                "update compra set cantidad={0} where idS={1} and nro_carrito={2}".format(cant_aux-cant, ids_aux, id_carrito)
                            )

                            #encuentro el valor final temporal que lleva el carrito
                            rows = session.execute(
                                "select valorfinal from carrito where idc={0} allow filtering".format(id_carrito)
                            )
                            aux = rows[0].valorfinal

                            #encuentro el precio del producto p
                            rows = session.execute(
                                "select precio from producto where idP={0} allow filtering".format(p)
                            )
                            vp = rows[0].precio

                            #Actualizo el valor final temporal del carrito con lo que tenia + precio del producto
                            session.execute(
                                "update carrito set valorfinal={0} where idC={1}".format(aux-(vp*cant), id_carrito)
                            )
                elif x[0] == 'terminar':
                    #actualizamos el estado del carrito
                    session.execute(
                        "update carrito set estado={0} where idC={1}".format(2, id_carrito)
                    )

                    #Traemos el valor final de la compra
                    rows = session.execute(
                        "select valorfinal from carrito where idC={0} allow filtering".format(id_carrito)
                    )
                    vf = rows[0].valorfinal
                    print("El total a pagar de su compra es de {0} $".format(vf))
                    print("Gracias por su compra!")
                    break
                elif x[0] == 'descartar':
                    #actualizamos el estado del carrito a inactivo pues se descarto la compra
                    session.execute(
                        "update carrito set estado={0} where idC={1}".format(3, id_carrito)
                    )
                    break
                ans = stdin.readline().strip()

        else:
            break
            login()
        print("Si desea realizar otra compra presione 1")
        print("Si desea cerrar sesion presione 2")
        print("Si desea salir presione 3")
        shop = int(stdin.readline().strip())

        if shop == 2:
            login()
        if shop == 3 or shop == 0:
            break

def main():
    global session, cluster
    cluster = Cluster(contact_points=['127.0.0.1'], port=9042)
    session = cluster.connect("bd13")
    print("Bienvenido, presione 1 para registrarse y 2 para iniciar sesion")
    ans = int(stdin.readline().strip())
    if ans == 1:
        create_user()
    elif ans == 2:
        login()

main()
