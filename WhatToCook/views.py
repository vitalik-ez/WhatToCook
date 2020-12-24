from django.shortcuts import render

# Create your views here.

from django.db import connection

from django.contrib.auth.hashers import make_password, check_password
from django.views import View
from django.shortcuts import redirect


class LoginView(View):

	def get(self, request):
		return render(request, 'index.html', {})

	def post(self, request):
		login = request.POST.get('login')
		password = request.POST.get('psw')

		with connection.cursor() as c:
			c.execute("SELECT * FROM user WHERE login = '{}' AND password = '{}'".format(login,password))
			result = c.fetchone()
			if result:
				request.session['user_id'] = result[0]
				return redirect('recommendation')
			

		return redirect('login')


import json
def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]

class RecommendationView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT id_category, value FROM user_category WHERE id_user = {}".format(request.session['user_id']))

			categories = c.fetchall()
			max_size = 10
			total = sum([ i[1] for i in categories])
			percentage = [ i[1]/total for i in categories]
			correlation = [ round(i * max_size) for i in percentage]
			recipe_result = []
			for index,i in enumerate(categories):
				c.execute("SELECT recipe_id FROM recipe_has_category WHERE category_id = {}".format(i[0]))
				recipe_id = c.fetchall()
				recipe_id = [ i[0] for i in recipe_id]
				c.execute("SELECT favourite.recipe_id, COUNT(*) FROM favourite WHERE recipe_id IN {} GROUP BY favourite.recipe_id".format(tuple(recipe_id)))
				recipe_count = c.fetchall()
				recipe_count = [ i for i in recipe_count]
				recipe_count = list(sorted(recipe_count, key=lambda x: x[1]))
				print("recipe sorted", recipe_count)

				if len(recipe_count) > correlation[index]:
					recipe_count = recipe_count[:correlation[index]]
				elif len(recipe_count) < correlation[index]:
					for i in recipe_id:
						if i not in [ j[0] for j in recipe_count]:
							recipe_count.append((i, 0))
					if len(recipe_count) > correlation[index]:
						recipe_count = recipe_count[:correlation[index]]
				print(recipe_count, "count result")
				recipe_result.extend(recipe_count)
			print("Beore", recipe_result)
			recipe_result = [ i[0] for i in recipe_result]

			print("XXXXXXXXX", recipe_result)
			if len(recipe_result) == 1:
				recipe_result = "({})".format(recipe_result[0])
			else:
				recipe_result = tuple(recipe_result)

			if len(recipe_result) != 0:
				c.execute("SELECT * FROM recipe WHERE id IN {}".format(recipe_result))
				final_recipes = dictfetchall(c)

				for i in final_recipes:
					if i['likes_id'] is not None:
						c.execute("SELECT count, id FROM likes WHERE id = {}".format(i['likes_id']))
						i['mark'] = range(int(c.fetchone()[0]))
					else:
						i['mark'] = False

			else:
				c.execute("SELECT * FROM recipe WHERE id IN (2,6,9,11)")
				final_recipes = dictfetchall(c)
				for i in final_recipes:
					if i['likes_id'] is not None:
						c.execute("SELECT count, id FROM likes WHERE id = {}".format(i['likes_id']))
						i['mark'] = range(int(c.fetchone()[0]))
					else:
						i['mark'] = False

			c.execute("SELECT id, name FROM recipe")

			recipe = dictfetchall(c)



		context = {}
		context['search_recipe'] = json.dumps(recipe)
		for i in final_recipes:
			i['summary'] = i['summary'][:60] + "..."
		context['recommendation'] = final_recipes


		return render(request, 'recommendation.html', context)

	def post(self, request):
		

		return render(request, 'recipe.html', {})




class RecipeNameView(View):
	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT * FROM recipe WHERE id = {}".format(pk))
			recipe = dictfetchall(c)

			recipe[0]['description'] = recipe[0]['description'].split("$")

			c.execute("SELECT product.name, count, measurement FROM productamount JOIN recipe_has_product_amount ON recipe_has_product_amount.recipe_id = {} AND recipe_has_product_amount.product_amount_id = productamount.id JOIN product ON product.id = productamount.product_id;".format(pk))
			product_amount = dictfetchall(c)

			c.execute("SELECT EXISTS(SELECT id FROM favourite WHERE user_id = {} and recipe_id = {})".format(request.session['user_id'], pk))
			result = c.fetchone()
			count = [0]
			is_marked = 0
			if recipe[0]['likes_id'] is not None:
				c.execute("SELECT COUNT(*) FROM likes_user WHERE id_likes = {} and id_like_user = {}".format(recipe[0]['likes_id'], request.session['user_id']))
				is_marked = c.fetchone()

				is_marked = True if is_marked[0] != 0 else False

				c.execute("SELECT count FROM likes WHERE id = {}".format(recipe[0]['likes_id']))

				count = c.fetchone()

			c.execute("SELECT text, id_user FROM comment_recipe WHERE recipe_id = {}".format(pk))
			comments = c.fetchall()

			user_id = tuple([ i[1] for i in comments])
			has_comments = True
			users = ()
			if len(user_id) == 0:
				has_comments = False
			elif len(user_id) == 1:
				user_id = "({})".format(user_id[0])

			if has_comments:
				c.execute("SELECT id, login FROM user WHERE id IN {}".format(user_id))
				users = c.fetchall()

			comments = list(comments)
			comments = list(sorted(comments, key=lambda x: x[1]))

			users = list(users)
			users = list(sorted(users, key=lambda x: x[0]))

			#comments = list(zip(comments, users))
			final_comments = []
			for i in comments:
				for j in users:
					if j[0] == i[1]:
						final_comments.append((i, j))


		return render(request, 'recipe_name.html', {'recipe':recipe, 'product_amount': product_amount, 'is_favourite': result[0], 'count': range(int(count[0])), 'is_marked': is_marked, 'comments': final_comments})

	def post(self, request, pk):
		with connection.cursor() as c:
			c.execute("INSERT INTO comment_recipe SET text = '{}', recipe_id = {}, id_user= {}".format(request.POST['comment'], pk, request.session['user_id']))

		return redirect('recipe_name', pk=pk)


def mark(request, pk, recipe):
	print(recipe)
	print(pk)
	with connection.cursor() as c:
		c.execute("SELECT likes_id FROM recipe WHERE id = {}".format(recipe))
		likes_id = c.fetchone()
		likes_id = likes_id[0]
		if likes_id is None:
			c.execute("INSERT INTO likes SET count = {}".format(pk))
			c.execute("SELECT id FROM likes WHERE id = LAST_INSERT_ID()")
			id_like = c.fetchone()
			id_like = id_like[0]
			c.execute("UPDATE recipe SET likes_id = {} WHERE id = {}".format(id_like, recipe))

			c.execute("INSERT INTO likes_user SET id_like_user = {}, id_likes = {}".format(request.session['user_id'], id_like))

		else:
			c.execute("SELECT id_like_user FROM likes_user WHERE id_like_user = {} AND id_likes = {}".format(request.session['user_id'], likes_id))
			id_like_user = c.fetchone()
			if id_like_user is None:
				c.execute("INSERT INTO likes_user SET id_likes = {}, id_like_user = {}".format(likes_id, request.session['user_id']))
				c.execute("SELECT COUNT(*) FROM likes_user WHERE id_likes = {}".format(likes_id))

				count = c.fetchone()
				c.execute("SELECT count FROM likes WHERE id = {}".format(likes_id))
				count_likes = c.fetchone()

				result = count_likes[0] + (pk - count_likes[0]) / count[0]

				c.execute("UPDATE likes SET count = {} WHERE id = {}".format(int(result), likes_id))

	return redirect('recipe_name', pk=recipe)

def like(request, pk):
	with connection.cursor() as c:
		c.execute("INSERT INTO favourite(user_id, recipe_id) values({},{})".format(request.session['user_id'], pk))
		recipe = dictfetchall(c)
		c.execute("SELECT category_id FROM recipe_has_category WHERE recipe_id = {}".format(pk))
		category_id = c.fetchone()
		c.execute("SELECT COUNT(*) FROM user_category WHERE id_category = {} and id_user = {}".format(category_id[0], request.session['user_id']))
		count = c.fetchone()
		if count[0] == 0:
			c.execute("INSERT INTO user_category(id_user, id_category, value) values({},{},{})".format(request.session['user_id'], category_id[0], 1))
		else:
			c.execute("UPDATE user_category SET value = value + 1 WHERE id_user = {} and id_category = {}".format(request.session['user_id'], category_id[0]))



	return redirect('recipe_name', pk=pk)


class RecipeView(View):

	def get(self, request):

		return render(request, 'recipe.html', {})

	def post(self, request):
		

		return render(request, 'recipe.html', {})



class ListView(View):
	def get(self, request, pk):
		if request.session['pk'] == 3:
			with connection.cursor() as c:
				c.execute("SELECT productamount.product_id FROM productamount JOIN products_for_recipes ON products_for_recipes.user_id = {} AND productamount.id = products_for_recipes.products_amount".format(request.session['user_id']))
				product_id = c.fetchall()

				if len(product_id) == 0:
					return render(request, 'list.html', {})


				list_id = []
				for i in product_id:
					list_id.append(i[0])

				if len(tuple(list_id)) == 1:
					list_id = "({})".format(tuple(list_id)[0])
				else:
					list_id = tuple(list_id)


				c.execute("SELECT recipe_id FROM recipe_has_product_amount JOIN productamount ON productamount.product_id IN {} AND recipe_has_product_amount.product_amount_id = productamount.id;".format(list_id))
				recipe_id = c.fetchall()

				if len(recipe_id) == 0:
					return render(request, 'list.html', {})

				recipe_list_id = []
				for i in recipe_id:
					recipe_list_id.append(i[0])

				if len(tuple(recipe_list_id)) == 1:
					recipe_list_id = "({})".format(tuple(recipe_list_id)[0])
				else:
					recipe_list_id = tuple(recipe_list_id)


				c.execute("SELECT recipe_id FROM recipe_has_category WHERE recipe_id IN {} AND category_id = {};".format(recipe_list_id, pk))
				recipe_id = c.fetchall()

				if len(recipe_id) == 0:
					return render(request, 'list.html', {})

				recipe_list_id = []
				for i in recipe_id:
					recipe_list_id.append(i[0])

				if len(tuple(recipe_list_id)) == 1:
					recipe_list_id = "({})".format(tuple(recipe_list_id)[0])
				else:
					recipe_list_id = tuple(recipe_list_id)

				c.execute("SELECT COUNT(*) AS count_product, recipe_id FROM recipe_has_product_amount WHERE product_amount_id IN (SELECT id FROM productamount WHERE product_id IN {} ) AND recipe_id IN {} GROUP BY recipe_id;".format(list_id, recipe_list_id))
				result = c.fetchall()

				if len(result) == 0:
					return render(request, 'list.html', {})

				result = sorted(result, key=lambda x: x[0])
				size = len(result) if len(result) <= 6 else 6
				result = result[:size]
				print(result) 

				recipe_id = []
				for i in result:
					recipe_id.append(i[1])
				print(recipe_id)
				if len(tuple(recipe_id)) == 1:
					recipe_id = "({})".format(tuple(recipe_id)[0])
				else:
					recipe_id = tuple(recipe_id)

				c.execute("SELECT id, name, summary, photo, likes_id FROM recipe WHERE id in {}".format(recipe_id))
				result = c.fetchall()

				list_result = []
				for i in result:
					short_description = i[2][:42] + "..."
					tmp = (i[0], i[1], short_description, i[3], i[4])
					list_result.append(tmp)
					

				final_list = []
				for i in list_result:
					if i[4] is not None:
						c.execute("SELECT count FROM likes WHERE id = {}".format(i[4]))
						final_list.append((i[0], i[1], i[2], i[3], i[4], range(int(c.fetchone()[0]))))
					else:
						final_list.append((i[0], i[1], i[2], i[3], i[4], False))

				list_result = final_list
				return render(request, 'list.html', {'result': list_result})

		else:	
			with connection.cursor() as c:
				c.execute("SELECT productamount.product_id FROM productamount JOIN refrigerator ON refrigerator.id_user = {} AND productamount.id = refrigerator.product_amount_id".format(request.session['user_id']))
				product_id = c.fetchall()

				if len(product_id) == 0:
					return render(request, 'list.html', {})


				list_id = []
				for i in product_id:
					list_id.append(i[0])

				if len(tuple(list_id)) == 1:
					list_id = "({})".format(tuple(list_id)[0])
				else:
					list_id = tuple(list_id)


				c.execute("SELECT recipe_id FROM recipe_has_product_amount JOIN productamount ON productamount.product_id IN {} AND recipe_has_product_amount.product_amount_id = productamount.id;".format(list_id))
				recipe_id = c.fetchall()

				if len(recipe_id) == 0:
					return render(request, 'list.html', {})

				recipe_list_id = []
				for i in recipe_id:
					recipe_list_id.append(i[0])

				if len(tuple(recipe_list_id)) == 1:
					recipe_list_id = "({})".format(tuple(recipe_list_id)[0])
				else:
					recipe_list_id = tuple(recipe_list_id)


				c.execute("SELECT recipe_id FROM recipe_has_category WHERE recipe_id IN {} AND category_id = {};".format(recipe_list_id, pk))
				recipe_id = c.fetchall()

				if len(recipe_id) == 0:
					return render(request, 'list.html', {})

				recipe_list_id = []
				for i in recipe_id:
					recipe_list_id.append(i[0])

				if len(tuple(recipe_list_id)) == 1:
					recipe_list_id = "({})".format(tuple(recipe_list_id)[0])
				else:
					recipe_list_id = tuple(recipe_list_id)

				c.execute("SELECT COUNT(*) AS count_product, recipe_id FROM recipe_has_product_amount WHERE product_amount_id IN (SELECT id FROM productamount WHERE product_id IN {} ) AND recipe_id IN {} GROUP BY recipe_id;".format(list_id, recipe_list_id))
				result = c.fetchall()

				if len(result) == 0:
					return render(request, 'list.html', {})

				result = sorted(result, key=lambda x: x[0])
				size = len(result) if len(result) <= 6 else 6
				result = result[:size]
				print(result) 

				recipe_id = []
				for i in result:
					recipe_id.append(i[1])
				print(recipe_id)
				if len(tuple(recipe_id)) == 1:
					recipe_id = "({})".format(tuple(recipe_id)[0])
				else:
					recipe_id = tuple(recipe_id)

				c.execute("SELECT id, name, summary, photo, likes_id FROM recipe WHERE id in {}".format(recipe_id))
				result = c.fetchall()


				list_result = []
				for i in result:
					short_description = i[2][:42] + "..."
					tmp = (i[0], i[1], short_description, i[3], i[4])
					list_result.append(tmp)
				
				final_list = []
				for i in list_result:
					if i[4] is not None:
						c.execute("SELECT count FROM likes WHERE id = {}".format(i[4]))
						final_list.append((i[0], i[1], i[2], i[3], i[4], range(int(c.fetchone()[0]))))
					else:
						final_list.append((i[0], i[1], i[2], i[3], i[4], False))

				list_result = final_list
				print(list_result, "ELSSSSSSSSSE")
				return render(request, 'list.html', {'result': list_result})

		
		return render(request, 'list.html', {})

	def post(self, request, pk):
		

		return render(request, 'recipe.html', {})



class ClassificationView(View):
	def get(self, request, pk):
		if pk == 2:
			return redirect('find_products_for_new_recipes')

		request.session['pk'] = pk
		with connection.cursor() as c:
			c.execute("SELECT * FROM category")
			categories = c.fetchall()
		
		return render(request, 'classification.html', {'categories':categories})

	def post(self, request, pk):
		

		return render(request, 'recipe.html', {})


class FindNewProductsView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT * FROM productamount JOIN products_for_recipes ON products_for_recipes.user_id = {} AND productamount.id = products_for_recipes.products_amount;".format(request.session['user_id']))
			product_amount = c.fetchall()
			print(product_amount)
			list_id = [ i[1] for i in product_amount ]
			
			if len(list_id) == 1:
				list_id = "({})".format(list_id[0])
			else:
				list_id = tuple(list_id)
			result = ()
			if len(list_id) != 0:
				print("SELECT * FROM product WHERE id IN {};".format(list_id))
				c.execute("SELECT * FROM product WHERE id IN {};".format(list_id))
				product = c.fetchall()

				print("2 product amount ",product_amount)
				print(product)

				list_product = []

				for i in product:
					list_product.append((i[0],i[1],"images/product_imgs/" + i[2] + ".png"))
				print(list_product)

				product_amount = sorted(product_amount, key=lambda x: x[1])
				result = list(zip(list_product, product_amount))
		
		with connection.cursor() as c:
			c.execute("SELECT id, name FROM whattocook.product WHERE id NOT IN (SELECT productamount.product_id FROM productamount JOIN products_for_recipes ON products_for_recipes.user_id = {} AND productamount.id = products_for_recipes.products_amount)".format(request.session['user_id']))
			products = dictfetchall(c)

		print("RESULT0",result)

		return render(request, 'find_products_for_new_fridge.html', {'result': result, 'search_products': json.dumps(products)})

	def post(self, request):
		

		return render(request, 'recipe.html', {})


class AddNewProductView(View):

	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT * FROM product WHERE id={}".format(pk))
			product = dictfetchall(c)
		for i in product:
			i['photo'] ="images/product_imgs/" + i['photo'] + ".png"

		return render(request, 'product.html', {'product': product})

	def post(self, request, pk):

		with connection.cursor() as c:
			c.execute("INSERT INTO productamount(product_id, count, measurement) values({},{},'{}')".format(pk, request.POST['count'], request.POST['measurement']))
			c.execute("INSERT INTO products_for_recipes(user_id, products_amount) values({}, (SELECT id FROM productamount WHERE id = LAST_INSERT_ID()))".format(request.session['user_id']))

		return redirect('find_products_for_new_recipes')



class SignupView(View):

	def get(self, request):
		print("GET")
		return render(request, 'signup.html', {})

	def post(self, request):
		print("POST")
		mail = request.POST.get('mail')
		psw = request.POST.get('psw')
		repeat_psw = request.POST.get('repeat_psw')
		login = request.POST.get('login')
		if psw != repeat_psw:
			return redirect('signup')
		with connection.cursor() as c:
			c.execute(f"SELECT * FROM user WHERE email = '{mail}' OR login = '{login}'")
			result = c.fetchall()
			if len(result) == 0:
				c.execute(f"INSERT INTO user (email, login, password) VALUES ('{mail}', '{login}', '{psw}');")
				return redirect('login')
	

		return redirect('signup')


def delete(request, pk):
	with connection.cursor() as c:
		c.execute("DELETE FROM productamount WHERE id = {} ".format(pk))
		c.execute("DELETE FROM refrigerator WHERE product_amount_id = {} ".format(pk))

	return redirect('refrigerator')

def delete_new(request, pk):
	with connection.cursor() as c:
		c.execute("DELETE FROM productamount WHERE id = {} ".format(pk))
		c.execute("DELETE FROM products_for_recipes WHERE products_amount = {} ".format(pk))

	return redirect('find_products_for_new_recipes')


class RefrigeratorView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT * FROM productamount JOIN refrigerator ON refrigerator.id_user = {} AND productamount.id = refrigerator.product_amount_id".format(request.session['user_id']))
			product_amount = c.fetchall()

			if len(product_amount) == 0:
					return render(request, 'refrigerator.html', {})

			list_id = [ i[1] for i in product_amount]

			if len(list_id) == 0:
				list_id = "()"
			elif len(list_id) == 1:
				list_id = "({})".format(list_id[0])
			else:
				list_id = tuple(list_id)

			c.execute("SELECT * FROM product WHERE id IN {}".format(list_id))
			product = c.fetchall()
			print(product_amount)
			print(product)

			list_product = []

			for i in product:
				list_product.append((i[0],i[1],"images/product_imgs/" + i[2] + ".png"))
			print(list_product)

		product_amount = sorted(product_amount, key=lambda x: x[1])
		result = list(zip(list_product, product_amount))
		
		print(result)
			
		return render(request, 'refrigerator.html', {'list_product': result})

	def post(self, request):
		current = request.POST.get('current')
		count = request.POST.get('count' + str(current))
		measurement = request.POST.get('measurement' + str(current))

		with connection.cursor() as c:
			c.execute("UPDATE productamount SET count = {}, measurement = '{}' WHERE id = {}".format(count, measurement, current))

		return redirect('refrigerator')



class FindProductsView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT id, name FROM whattocook.product WHERE id NOT IN (SELECT productamount.product_id FROM productamount JOIN refrigerator ON refrigerator.id_user = {} AND productamount.id = refrigerator.product_amount_id)".format(request.session['user_id']))
			products = dictfetchall(c)

		context = {}
		context['search_products'] = json.dumps(products)
		return render(request, 'find_products.html', context)

	def post(self, request):
		print("POST")
		return redirect('refrigerator')


class AddProductView(View):
	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT * FROM product WHERE id={}".format(pk))
			product = dictfetchall(c)
		for i in product:
			i['photo'] ="images/product_imgs/" + i['photo'] + ".png"

		return render(request, 'product.html', {'product': product})


	def post(self, request, pk):

		with connection.cursor() as c:
			c.execute("INSERT INTO productamount(product_id, count, measurement) values({},{},'{}')".format(pk, request.POST['count'], request.POST['measurement']))
			c.execute("INSERT INTO refrigerator(id_user, product_amount_id) values({}, (SELECT id FROM productamount WHERE id = LAST_INSERT_ID()))".format(request.session['user_id']))



		return redirect('find_products')




class FavoriteRecipesView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT recipe.id, name, photo, summary, likes_id FROM recipe JOIN favourite ON favourite.user_id = {} and favourite.recipe_id = recipe.id".format(request.session['user_id']))
			recipes = dictfetchall(c)

			count_list = []
			for i in recipes:
				if i['likes_id'] is not None:
					c.execute("SELECT count, id FROM likes WHERE id = {}".format(i['likes_id']))
					i['mark'] = range(int(c.fetchone()[0]))
				else:
					i['mark'] = False

			for i in recipes:
				i['summary'] = i['summary'][:42] + "..."
			


		return render(request, 'favorite_list.html', {'recipes': list(recipes)})


	def post(self, request):
		return redirect('recommendation')


def delete_favourite(request, pk):
	with connection.cursor() as c:
		c.execute("DELETE FROM favourite WHERE recipe_id = {} ".format(pk))
		c.execute("SELECT category_id FROM recipe_has_category WHERE recipe_id = {} ".format(pk))
		category_id = c.fetchone()
		c.execute("UPDATE user_category SET value = value - 1 WHERE id_category = {} and id_user = {} ".format(category_id[0], request.session['user_id']))
		
	return redirect('favorite_recipes')





class MyRecipesView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT * FROM recipesforcheck WHERE id_user = {}".format(request.session['user_id']))
			recipes = c.fetchall()
			print(recipes)
		return render(request, 'add_recipe.html', {'recipes': recipes})


	def post(self, request):
		return redirect('my_recipes')

from .forms import RecipeForm
from PIL import Image
class AddRecipesView(View):
	def get(self, request):
		print("Add recipe")
		recipe_form = RecipeForm()
		return render(request, 'add_r.html', {'recipe_form': recipe_form})


	def post(self, request):
		image = Image.open(request.FILES['photo'].file)
		image.save("static/upload_photo/" + request.FILES['photo'].name) 
		name_recipe = request.POST['name_recipe']
		description = request.POST['description']
		recipe = request.POST['recipe']
		category_id = int(request.POST['category_id'])
		with connection.cursor() as c:
			c.execute("INSERT INTO recipesforcheck SET summary = '{}', name = '{}', description = '{}', category_id = {}, photo = '{}', id_user = {}".format(description, name_recipe, recipe, category_id, "upload_photo/" + request.FILES['photo'].name, request.session['user_id']))
			c.execute("SELECT id FROM recipesforcheck WHERE id = LAST_INSERT_ID()")
			id_recipe = c.fetchone()
		
		return redirect('add_products_for_recipe', pk=id_recipe[0])

class AddRProductsForRecipeView(View):
	def get(self, request, pk):
		request.session['id_recipe'] = pk
		
		with connection.cursor() as c:
			c.execute("SELECT * FROM productamountforcheck JOIN recipesforcheck ON recipesforcheck.id = {} AND recipesforcheck.id = productamountforcheck.recipe_for_check_id;".format(pk))
			product_amount = c.fetchall()
			print(product_amount)
			list_id = [ i[1] for i in product_amount ]
			
			if len(list_id) == 1:
				list_id = "({})".format(list_id[0])
			else:
				list_id = tuple(list_id)
			result = ()
			if len(list_id) != 0:
				print("SELECT * FROM product WHERE id IN {};".format(list_id))
				c.execute("SELECT * FROM product WHERE id IN {};".format(list_id))
				product = c.fetchall()

				print("2 product amount ",product_amount)
				print(product)

				list_product = []

				for i in product:
					list_product.append((i[0],i[1],"images/product_imgs/" + i[2] + ".png"))
				print(list_product)

				product_amount = sorted(product_amount, key=lambda x: x[1])
				result = list(zip(list_product, product_amount))
		
		with connection.cursor() as c:
			c.execute("SELECT id, name FROM whattocook.product WHERE id NOT IN (SELECT productamount.product_id FROM productamount JOIN products_for_recipes ON products_for_recipes.user_id = {} AND productamount.id = products_for_recipes.products_amount)".format(request.session['user_id']))
			products = dictfetchall(c)

		return render(request, 'add_products_for_recipe.html', {'result': result, 'search_products': json.dumps(products)})


	def post(self, request, pk):
		
		
		return redirect('my_recipes')


class AddProducRecipeView(View):
	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT * FROM product WHERE id={}".format(pk))
			product = dictfetchall(c)
		for i in product:
			i['photo'] ="images/product_imgs/" + i['photo'] + ".png"

		return render(request, 'new_product.html', {'product': product, 'recipe_id': request.session['id_recipe']})


	def post(self, request, pk):

		with connection.cursor() as c:
			c.execute("INSERT INTO productamountforcheck(product_id, count, measurement, recipe_for_check_id) values({},{},'{}', {})".format(pk, request.POST['count'], request.POST['measurement'], request.session['id_recipe']))


		return redirect('add_products_for_recipe', pk=request.session['id_recipe'])	


class SettingsView(View):
	def get(self, request):
		print("Settings")
		return render(request, 'Settings.html', {})


	def post(self, request):
		return redirect('my_recipes')

class ProfileView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT email, login FROM user WHERE id = {}".format(request.session['user_id']))
			user = c.fetchone()
			c.execute("SELECT * FROM admin WHERE user_id = {}".format(request.session['user_id']))
			is_admin = c.fetchone()
		print(is_admin)
		is_admin = True if is_admin else False 
		print(is_admin, "ASSS")
		return render(request, 'profile.html', {'user':user, 'is_admin': is_admin})


	def post(self, request):
		return redirect('my_recipes')

class SubscribeView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT balance FROM user WHERE id = {}".format(request.session['user_id']))
			balance = c.fetchone()

			c.execute("SELECT duration FROM subscribe WHERE user_id = {}".format(request.session['user_id']))

			duration = c.fetchone()

		return render(request, 'subscribe.html', {'balance': balance[0], 'duration': duration})


	def post(self, request):
		with connection.cursor() as c:
			c.execute("SELECT balance FROM user WHERE id = {}".format(request.session['user_id']))
			balance = c.fetchone()[0]
			if balance >= 9:
				c.execute("UPDATE user SET balance = balance - 10 WHERE id = {}".format(request.session['user_id']))

				c.execute("INSERT INTO subscribe SET user_id = {}, duration = NOW() + INTERVAL 1 MONTH".format(request.session['user_id']))

		return redirect('subscribe')



def privacy(request):
	return render(request, 'privacy.html', {})




class NewRecipeNameView(View):
	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT * FROM recipesforcheck WHERE id = {}".format(pk))
			recipe = dictfetchall(c)

			recipe[0]['description'] = recipe[0]['description'].split("$")

			c.execute("SELECT product.name, count, measurement FROM productamountforcheck JOIN recipesforcheck ON recipesforcheck.id = {} JOIN product ON product.id = productamountforcheck.product_id;".format(pk))
			product_amount = dictfetchall(c)

			


		return render(request, 'add_recipe_name.html', {'recipe':recipe, 'product_amount': product_amount})

	def post(self, request, pk):
		with connection.cursor() as c:
			c.execute("INSERT INTO comment_recipe SET text = '{}', recipe_id = {}, id_user= {}".format(request.POST['comment'], pk, request.session['user_id']))

		return redirect('recipe_name', pk=pk)


def ChangeEmail(request):
	with connection.cursor() as c:
		c.execute("SELECT * FROM user WHERE email = '{}'".format(request.POST['email']))
		result = c.fetchone()
		if not result:
			c.execute("UPDATE user SET email = '{}' WHERE id = {}".format(request.POST['email'], request.session['user_id']))


	return render(request, 'settings_email.html', {'is_email': True, 'is_login': False, 'is_password': False, 'is_success': not result})

def ChangeLogin(request):
	with connection.cursor() as c:
		c.execute("SELECT * FROM user WHERE login = '{}'".format(request.POST['login']))
		result = c.fetchone()
		if not result:
			c.execute("UPDATE user SET login = '{}' WHERE id = {}".format(request.POST['login'], request.session['user_id']))


	return render(request, 'settings_email.html', {'is_email': False, 'is_login': True, 'is_password': False, 'is_success': not result})

	

def ChangePassword(request):
	with connection.cursor() as c:
		if request.POST['password'] == request.POST['repeat_password']:
			c.execute("UPDATE user SET password = '{}' WHERE id = {}".format(request.POST['password'], request.session['user_id']))

	return render(request, 'settings_email.html', {'is_email': False, 'is_login': False, 'is_password': True, 'is_success': request.POST['password'] == request.POST['repeat_password']})


class AdminPanelView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT rights FROM admin WHERE user_id = {}".format(request.session['user_id']))
			rights = c.fetchone()

			c.execute("SELECT login, email FROM user WHERE id = {}".format(request.session['user_id']))
			user = c.fetchone()

		success = try1 = False
		if 'success' in request.session and 'try' in request.session:
			success = request.session['success']
			try1 = request.session['try']	
			request.session['success'] = False
			request.session['try'] = False

		return render(request, 'admin.html', {'user':user, 'rights': rights, 'success': success, 'try': try1})


	def post(self, request):
		is_admin = 0
		with connection.cursor() as c:
			c.execute("SELECT id FROM user WHERE login = '{}' or email = '{}'".format(request.POST['admin'], request.POST['admin']))
			result = c.fetchone()
			if result:
				c.execute("SELECT * FROM admin WHERE user_id = {}".format(result[0]))
				is_admin = c.fetchone()

				if not is_admin:
					c.execute("INSERT INTO admin SET user_id = {}, rights = 'Адміністратор'".format(result[0]))
				
		request.session['success'] = not is_admin
		request.session['try'] = True

		return redirect('admin_panel')



class AdminListView(View):
	def get(self, request):
		with connection.cursor() as c:
			c.execute("SELECT id, name, summary, photo FROM recipesforcheck WHERE status = 0")
			recipesforcheck = dictfetchall(c)
			print(recipesforcheck)
		
		return render(request, 'admin_list.html', {'recipes': recipesforcheck})


	def post(self, request):
		
		return redirect('admin_panel')


class RecipeReviewView(View):
	def get(self, request, pk):
		with connection.cursor() as c:
			c.execute("SELECT id, name, summary, photo, description FROM recipesforcheck WHERE id = {}".format(pk))
			recipesforcheck = dictfetchall(c)

			c.execute("SELECT product.name, count, measurement  FROM productamountforcheck JOIN product ON product.id = productamountforcheck.product_id WHERE productamountforcheck.recipe_for_check_id = {}".format(pk))
			product_amount = dictfetchall(c)

		return render(request, 'recipe_review.html', {'recipe': recipesforcheck, 'product_amount': product_amount})


	def post(self, request, pk):
		
		return redirect('admin_panel')


def SaveNewRecipe(request, pk):
	with connection.cursor() as c:
		c.execute("SELECT * FROM recipesforcheck WHERE id = {}".format(pk))
		recipe = c.fetchone()

		c.execute("SELECT * FROM productamountforcheck WHERE recipe_for_check_id = {}".format(pk))
		product_amount = dictfetchall(c)

		c.execute("INSERT INTO recipe(name, description,photo, summary) values('{}','{}','{}', '{}')".format(recipe[2], recipe[3], recipe[6], recipe[1]))
		

		c.execute("SELECT id FROM recipe WHERE id = LAST_INSERT_ID()")
		id_recipe = c.fetchone()
		c.execute("INSERT INTO recipe_has_category(recipe_id, category_id) values({},{})".format(id_recipe[0],recipe[4]))

		for i in product_amount:
			c.execute("INSERT INTO productamount(product_id, count,measurement) values({},{},'{}')".format(i['product_id'], i['count'], i['measurement']))
			c.execute("SELECT id FROM productamount WHERE id = LAST_INSERT_ID()")
			id_product_amount = c.fetchone()
			c.execute("INSERT INTO recipe_has_product_amount(recipe_id, product_amount_id) values({},{})".format(id_recipe[0], id_product_amount[0]))

		c.execute("UPDATE recipesforcheck SET status = 1 WHERE id = {}".format(pk))

		c.execute("UPDATE user SET balance = balance + 10 WHERE id = {}".format(recipe[7]))
		return redirect('admin_list')


def DeleteNewRecipe(request, pk):
	with connection.cursor() as c:
		c.execute("DELETE FROM productamountforcheck WHERE recipe_for_check_id = {}".format(pk))
		c.execute("DELETE FROM recipesforcheck WHERE id = {}".format(pk))
	return redirect('admin_list')
	
