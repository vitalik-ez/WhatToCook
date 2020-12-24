from django.urls import path

from . import views

urlpatterns = [
    path('', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('recipe/', views.RecipeView.as_view(), name='recipe'),
    path('classification/<int:pk>/', views.ClassificationView.as_view(), name='classification'),


    path('recommendation/', views.RecommendationView.as_view(), name='recommendation'),

    path('list/<int:pk>', views.ListView.as_view(), name='list'),

    path('refrigerator/', views.RefrigeratorView.as_view(), name='refrigerator'),


	path('recipe_name/<int:pk>', views.RecipeNameView.as_view(), name='recipe_name'),
    path('recommendation/recipe_name/<int:pk>', views.RecipeNameView.as_view(), name='recipe_name_recommendation'),


    path('like_recipe/<int:pk>', views.like, name='like'),

    path('mark_recipe/<int:pk>/<int:recipe>', views.mark, name='mark_recipe'),
    

    path('delete/<int:pk>', views.delete, name='delete'),

    path('delete_favourite/<int:pk>', views.delete_favourite, name='delete_favourite'),

    path('delete_new/<int:pk>', views.delete_new, name='delete_new'),

    path('find_products/', views.FindProductsView.as_view(), name='find_products'),
    path('find_products/add_product/<int:pk>', views.AddProductView.as_view(), name='add_product'),



    path('favorite_recipes/', views.FavoriteRecipesView.as_view(), name='favorite_recipes'),

    path('find_products_for_new_recipes/', views.FindNewProductsView.as_view(), name='find_products_for_new_recipes'),

    path('find_products_for_new_recipes/add_new_product/<int:pk>', views.AddNewProductView.as_view(), name='add_new_product'),
    



    path('my_recipes/', views.MyRecipesView.as_view(), name='my_recipes'),
    path('my_recipes/add', views.AddRecipesView.as_view(), name='add_recipe'),
    path('add_products_for_recipe/<int:pk>', views.AddRProductsForRecipeView.as_view(), name='add_products_for_recipe'),

    path('add_products_for_recipe/add_new_product_recipe/<int:pk>', views.AddProducRecipeView.as_view(), name='add_product_recipe'),

    path('new_recipe_name/<int:pk>', views.NewRecipeNameView.as_view(), name='new_recipe_name'),




    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),


    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('privacy/', views.privacy, name='privacy'),


    path('change_email/', views.ChangeEmail, name='change_email'),
    path('change_login/', views.ChangeLogin, name='change_login'),
    path('change_password/', views.ChangePassword, name='change_password'),

    path('admin_panel/', views.AdminPanelView.as_view(), name='admin_panel'),
    path('admin_list/', views.AdminListView.as_view(), name='admin_list'),

    path('save_new_recipe/<int:pk>', views.SaveNewRecipe, name='save_new_recipe'),
    path('delete_new_recipe/<int:pk>', views.DeleteNewRecipe, name='delete_new_recipe'),
    path('recipe_review/<int:pk>', views.RecipeReviewView.as_view(), name='recipe_review'),



]


